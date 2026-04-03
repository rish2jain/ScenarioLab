"""Simulation agent with LLM-driven reasoning."""

import logging
import uuid
from datetime import datetime, timezone

from app.llm.provider import LLMMessage, LLMProvider
from app.personas.archetypes import ArchetypeDefinition
from app.simulation.models import (
    AgentConfig,
    AgentState,
    SimulationMessage,
)

logger = logging.getLogger(__name__)


class SimulationAgent:
    """An agent with persona, memory, and LLM-driven reasoning."""

    def __init__(
        self,
        config: AgentConfig,
        archetype: ArchetypeDefinition,
        llm_provider: LLMProvider,
        memory_manager=None,
    ):
        self.id = config.id or str(uuid.uuid4())
        self.name = config.name
        self.archetype = archetype
        self.llm = llm_provider
        self.memory = memory_manager
        self.customization = config.customization

        # Build the full persona prompt
        persona_prompt = self._build_persona_prompt(config.customization)

        self.state = AgentState(
            id=self.id,
            name=self.name,
            archetype_id=archetype.id,
            persona_prompt=persona_prompt,
            current_stance="",
            coalition_members=[],
            vote_history=[],
        )

        logger.info(f"Initialized agent {self.name} ({archetype.role})")

    def _build_persona_prompt(self, customization: dict) -> str:
        """Build the full system prompt from archetype template."""
        template = self.archetype.system_prompt_template

        # Prepare context string
        context = customization.get("context", "")
        if not context:
            context = (
                "You are participating in a strategic war-game simulation."
            )

        # Use safe substitution to avoid KeyError/ValueError on user content
        # containing braces like {json} or {data}
        try:
            prompt = template.format(
                role=self.archetype.role,
                context=context,
            )
        except (KeyError, ValueError):
            # Fallback: manual replacement if template has unexpected placeholders
            prompt = template.replace("{role}", self.archetype.role)
            prompt = prompt.replace("{context}", context)

        # Add customization overrides
        if customization:
            prompt += "\n\nCUSTOMIZATION:\n"
            for key, value in customization.items():
                if key != "context":
                    prompt += f"- {key}: {value}\n"

        return prompt

    async def generate_response(
        self,
        context: str,
        phase: str,
        round_number: int,
        visible_messages: list[SimulationMessage],
        instruction: str = "",
    ) -> SimulationMessage:
        """Generate agent's response for the current phase."""
        try:
            # Build the prompt
            messages = self._build_prompt(
                context=context,
                phase=phase,
                round_number=round_number,
                visible_messages=visible_messages,
                instruction=instruction,
            )

            # Call LLM
            response = await self.llm.generate(
                messages=messages,
                temperature=0.7,
                max_tokens=1024,
            )

            # Determine message type based on content
            message_type = self._classify_message_type(response.content, phase)

            # Create the message
            message = SimulationMessage(
                round_number=round_number,
                phase=phase,
                agent_id=self.id,
                agent_name=self.name,
                agent_role=self.archetype.role,
                content=response.content.strip(),
                message_type=message_type,
                visibility="public",
            )

            logger.debug(
                f"Agent {self.name} generated response in phase {phase}"
            )
            return message

        except Exception as e:
            logger.error(
                f"Failed to generate response for agent {self.name}: {e}"
            )
            # Return a fallback message
            return SimulationMessage(
                round_number=round_number,
                phase=phase,
                agent_id=self.id,
                agent_name=self.name,
                agent_role=self.archetype.role,
                content=f"[Error generating response: {str(e)}]",
                message_type="error",
                visibility="public",
            )

    def _build_prompt(
        self,
        context: str,
        phase: str,
        round_number: int,
        visible_messages: list[SimulationMessage],
        instruction: str,
    ) -> list[LLMMessage]:
        """Build the LLM prompt for response generation."""
        messages = []

        # 1. System prompt (persona)
        messages.append(
            LLMMessage(role="system", content=self.state.persona_prompt)
        )

        # 2. Simulation context
        context_parts = []
        if context:
            context_parts.append(f"SIMULATION CONTEXT:\n{context}")

        context_parts.append(f"CURRENT ROUND: {round_number}")
        context_parts.append(f"CURRENT PHASE: {phase}")

        if self.state.current_stance:
            context_parts.append(
                f"YOUR CURRENT STANCE: {self.state.current_stance}"
            )

        if self.state.coalition_members:
            allies = ", ".join(self.state.coalition_members)
            context_parts.append(f"YOUR COALITION ALLIES: {allies}")

        messages.append(
            LLMMessage(role="user", content="\n\n".join(context_parts))
        )

        # 3. Recent conversation history
        if visible_messages:
            history = "\n\n".join([
                f"{msg.agent_name} ({msg.agent_role}): {msg.content}"
                for msg in visible_messages[-10:]  # Last 10 messages
            ])
            messages.append(
                LLMMessage(
                    role="user", content=f"RECENT CONVERSATION:\n{history}"
                )
            )

        # 4. Phase-specific instruction
        if instruction:
            messages.append(
                LLMMessage(role="user", content=f"INSTRUCTION: {instruction}")
            )

        # 5. Final prompt
        messages.append(
            LLMMessage(
                role="user",
                content="Provide your response as your character would speak.",
            )
        )

        return messages

    def _classify_message_type(self, content: str, phase: str) -> str:
        """Classify the type of message based on content."""
        content_lower = content.lower()

        if phase == "vote":
            return "vote"
        elif phase == "decision":
            return "decision"
        elif "?" in content:
            return "question"
        elif any(word in content_lower
                 for word in ["object", "oppose", "disagree"]):
            return "objection"
        elif any(word in content_lower
                 for word in ["support", "agree", "endorse"]):
            return "support"
        else:
            return "statement"

    async def cast_vote(
        self, proposal: str, arguments: list[SimulationMessage]
    ) -> dict:
        """Have the agent vote on a proposal."""
        try:
            # Build voting prompt
            messages = [
                LLMMessage(role="system", content=self.state.persona_prompt),
                LLMMessage(
                    role="user",
                    content=f"PROPOSAL TO VOTE ON:\n{proposal}",
                ),
            ]

            if arguments:
                args_text = "\n\n".join([
                    f"{msg.agent_name}: {msg.content}" for msg in arguments
                ])
                messages.append(
                    LLMMessage(role="user", content=f"ARGUMENTS:\n{args_text}")
                )

            messages.append(
                LLMMessage(
                    role="user",
                    content=(
                        "Cast your vote. Respond with ONLY one of: "
                        "'for', 'against', or 'abstain', followed by a "
                        "brief reasoning.\n\n"
                        "Format: VOTE: [for/against/abstain]\n"
                        "REASONING: [your reasoning]"
                    ),
                )
            )

            response = await self.llm.generate(
                messages=messages,
                temperature=0.5,
                max_tokens=256,
            )

            # Parse the vote
            content = response.content.lower()
            vote = "abstain"
            if "for" in content or "support" in content or "yes" in content:
                vote = "for"
            elif ("against" in content or "oppose" in content
                  or "no" in content):
                vote = "against"

            # Extract reasoning
            reasoning = response.content
            if "reasoning:" in content:
                reasoning = response.content.split("reasoning:", 1)[1].strip()

            result = {
                "agent_id": self.id,
                "agent_name": self.name,
                "vote": vote,
                "reasoning": reasoning,
            }

            # Record in history
            self.state.vote_history.append(result)

            return result

        except Exception as e:
            logger.error(f"Failed to cast vote for agent {self.name}: {e}")
            return {
                "agent_id": self.id,
                "agent_name": self.name,
                "vote": "abstain",
                "reasoning": f"Error during voting: {str(e)}",
            }

    async def update_stance(self, round_messages: list[SimulationMessage]):
        """Update agent's current stance based on round events."""
        try:
            if not round_messages:
                return

            # Build stance analysis prompt
            conversation = "\n\n".join([
                f"{msg.agent_name}: {msg.content}"
                for msg in round_messages[-5:]
            ])

            messages = [
                LLMMessage(role="system", content=self.state.persona_prompt),
                LLMMessage(
                    role="user",
                    content=(
                        "Based on this recent conversation, briefly "
                        "summarize your current stance/position "
                        f"(1-2 sentences).\n\nCONVERSATION:\n{conversation}"
                    ),
                ),
            ]

            response = await self.llm.generate(
                messages=messages,
                temperature=0.5,
                max_tokens=128,
            )

            self.state.current_stance = response.content.strip()
            logger.debug(
                f"Updated stance for {self.name}: {self.state.current_stance}"
            )

        except Exception as e:
            logger.error(f"Failed to update stance for agent {self.name}: {e}")

    async def store_memory(
        self,
        simulation_id: str,
        round_number: int,
        content: str,
        memory_type: str,
    ):
        """Store a memory from the current round."""
        if not self.memory:
            logger.debug(
                f"No memory manager for agent {self.name}, "
                "skipping memory storage"
            )
            return

        try:
            from app.graph.memory import MemoryEntry

            entry = MemoryEntry(
                id=str(uuid.uuid4()),
                agent_id=self.id,
                simulation_id=simulation_id,
                round_number=round_number,
                content=content,
                memory_type=memory_type,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

            await self.memory.add_memory(entry)
            logger.debug(f"Stored memory for agent {self.name}")

        except Exception as e:
            logger.error(f"Failed to store memory for agent {self.name}: {e}")
