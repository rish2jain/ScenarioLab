"""Simulation agent with LLM-driven reasoning."""

import asyncio
import logging
import re
import uuid
from datetime import datetime, timezone

from app.config import settings
from app.llm.inference_router import InferenceRouter
from app.llm.provider import LLMMessage, LLMResponse
from app.personas.archetypes import ArchetypeDefinition
from app.simulation.models import (
    AgentConfig,
    AgentState,
    SimulationMessage,
)

logger = logging.getLogger(__name__)

# Per running event loop — a single global Semaphore binds to
# one loop at creation time.
_llm_semaphores: dict[int, asyncio.Semaphore] = {}


# Remove entire reasoning blocks (multi-line), not only the boundary tags.
_THINK_BLOCK_RE = re.compile(
    r"(?:"
    r"<think\b[^>]*>.*?(?:`</redacted_thinking>`|</redacted_thinking>)"
    r"|<redacted_thinking\b[^>]*>.*?</redacted_thinking>"
    r")",
    re.DOTALL | re.IGNORECASE,
)
_ORPHAN_REASONING_TAG_RE = re.compile(
    r"</?(?:think|redacted_thinking)\b[^>]*>",
    re.IGNORECASE,
)
_NON_LATIN_HEAVY_RE = re.compile(
    r"[\u4e00-\u9fff\u3400-\u4dbf\uac00-\ud7af\u0400-\u04ff\u0600-\u06ff"
    r"\u0900-\u097f\u3040-\u309f\u30a0-\u30ff]"
)


def _strip_reasoning_markup(content: str) -> str:
    """Remove think/redacted_thinking blocks and stray tags."""
    cleaned = content
    for _ in range(32):
        nxt = _THINK_BLOCK_RE.sub("", cleaned)
        if nxt == cleaned:
            break
        cleaned = nxt
    cleaned = _ORPHAN_REASONING_TAG_RE.sub("", cleaned)
    cleaned = re.sub(r"[ \t]+\n", "\n", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def sanitize_llm_response(content: str) -> str:
    """Strip think-tags and detect likely non-English hallucinations.

    Returns cleaned content.  If the response is overwhelmingly non-Latin
    script (>40 % of alpha chars), replaces it with a flag string so
    downstream code can handle it.
    """
    if not content:
        return ""
    # Strip full reasoning blocks (including inner text), then stray tags
    cleaned = _strip_reasoning_markup(str(content))
    # Detect language drift: if >40% of characters are non-Latin script,
    # flag the response rather than passing garbage downstream
    alpha_chars = [c for c in cleaned if c.isalpha()]
    if alpha_chars:
        non_latin_count = len(_NON_LATIN_HEAVY_RE.findall(cleaned))
        if non_latin_count / len(alpha_chars) > 0.4:
            logger.warning(
                "LLM response appears to be non-English (%d/%d non-Latin "
                "chars); flagging as hallucination",
                non_latin_count,
                len(alpha_chars),
            )
            return "[HALLUCINATION_DETECTED: non-English response]"
    return cleaned


def parse_vote_from_response(content: str) -> str:
    """Extract for | against | abstain from model output.

    Prefer an explicit ``VOTE:`` line; fall back to word-boundary matching
    with ``against/oppose`` checked *before* ``for`` to avoid false positives
    like "I oppose this for good reasons" matching "for".
    """
    if not content or not str(content).strip():
        return "abstain"
    raw = sanitize_llm_response(str(content))
    if not raw or raw.startswith("[HALLUCINATION_DETECTED"):
        return "abstain"
    low = raw.lower()
    # 1. Structured VOTE: line (highest priority)
    m = re.search(
        r"(?im)^\s*VOTE\s*:\s*(for|against|abstain)\b",
        raw,
    )
    if not m:
        m = re.search(r"(?i)\bVOTE\s*:\s*(for|against|abstain)\b", raw)
    if m:
        return m.group(1).lower()
    # 2. Fallback: word boundaries, checked in safe order
    #    against/oppose BEFORE for to prevent "against X for Y" false positives
    if re.search(r"\babstain\b", low):
        return "abstain"
    if re.search(r"\bagainst\b", low) or re.search(r"\boppose\b", low):
        return "against"
    if re.search(r"\b(?:vote|am|voting)\s+for\b", low) or re.search(
        r"\byes\b", low
    ):
        return "for"
    if re.search(r"\bsupport\b", low) or re.search(r"\bapprove\b", low):
        return "for"
    return "abstain"


def _llm_limit_semaphore() -> asyncio.Semaphore:
    loop = asyncio.get_running_loop()
    key = id(loop)
    if key not in _llm_semaphores:
        n = max(1, int(settings.simulation_llm_parallelism))
        _llm_semaphores[key] = asyncio.Semaphore(n)
    return _llm_semaphores[key]


class SimulationAgent:
    """An agent with persona, memory, and LLM-driven reasoning."""

    def __init__(
        self,
        config: AgentConfig,
        archetype: ArchetypeDefinition,
        inference_router: InferenceRouter,
        memory_manager=None,
    ):
        self.id = config.id or str(uuid.uuid4())
        self.name = config.name
        self.archetype = archetype
        self.router = inference_router
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

    async def _throttled_generate(
        self,
        messages: list[LLMMessage],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        *,
        round_number: int = 1,
        task_type: str = "response",
        **kwargs,
    ) -> LLMResponse:
        provider = self.router.get_provider(round_number, task_type)
        if self.router.should_inject_exemplars(
            self.id, round_number, task_type
        ):
            exemplar_msgs = self.router.build_exemplar_messages(self.id)
            if exemplar_msgs:
                if not isinstance(messages, list):
                    logger.warning(
                        "Hybrid exemplar injection skipped: messages is not "
                        "a list (%s)",
                        type(messages).__name__,
                    )
                elif not messages:
                    messages = list(exemplar_msgs)
                elif getattr(messages[0], "role", None) == "system":
                    messages = [messages[0]] + exemplar_msgs + messages[1:]
                else:
                    logger.warning(
                        "Hybrid exemplar injection: first message is not system; "
                        "prepending exemplar messages"
                    )
                    messages = list(exemplar_msgs) + list(messages)
        async with _llm_limit_semaphore():
            return await provider.generate(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
            )

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

        # Add seed document context
        seed_ctx = customization.get("seed_context", "")
        if seed_ctx:
            prompt += (
                "\n\nSEED DOCUMENTS (reference material for "
                "this simulation):\n"
                f"{seed_ctx}\n"
            )

        ext_ctx = customization.get("external_research_context", "")
        if ext_ctx:
            prompt += (
                "\n\nEXTERNAL RESEARCH (web-sourced; do not invent facts "
                "beyond this block):\n"
                f"{ext_ctx}\n"
            )

        # Add customization overrides
        if customization:
            prompt += "\n\nCUSTOMIZATION:\n"
            skip = {"context", "seed_context", "external_research_context"}
            for key, value in customization.items():
                if key not in skip:
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

            # Call LLM (global concurrency cap across agents)
            response = await self._throttled_generate(
                messages=messages,
                temperature=0.7,
                max_tokens=1024,
                round_number=round_number,
                task_type="response",
            )

            # Sanitize: strip think-tags, detect language hallucinations
            cleaned = sanitize_llm_response(response.content)

            # Determine message type based on content
            message_type = self._classify_message_type(cleaned, phase)

            # Create the message
            message = SimulationMessage(
                round_number=round_number,
                phase=phase,
                agent_id=self.id,
                agent_name=self.name,
                agent_role=self.archetype.role,
                content=cleaned,
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
        self,
        proposal: str,
        arguments: list[SimulationMessage],
        *,
        round_number: int = 1,
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
                        "Cast your vote in English only. Respond with ONLY "
                        "one of: 'for', 'against', or 'abstain', followed by "
                        "brief reasoning.\n\n"
                        "Format: VOTE: [for/against/abstain]\n"
                        "REASONING: [your reasoning]"
                    ),
                )
            )

            response = await self._throttled_generate(
                messages=messages,
                temperature=0.5,
                max_tokens=256,
                round_number=round_number,
                task_type="vote",
            )

            vote = parse_vote_from_response(response.content)

            # Extract reasoning
            reasoning = response.content
            idx = response.content.lower().find("reasoning:")
            if idx != -1:
                reasoning = response.content[idx + 10:].strip()

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

    async def update_stance(
        self,
        round_messages: list[SimulationMessage],
        *,
        round_number: int = 1,
        max_retries: int = 2,
    ):
        """Update agent's current stance based on round events.

        Retries on empty/hallucinated results.  Preserves prior stance on
        total failure rather than leaving it blank.
        """
        if not round_messages:
            return

        prior_stance = self.state.current_stance

        # Use more messages for richer context (up to 10, not just 5)
        conversation = "\n\n".join([
            f"{msg.agent_name}: {msg.content}"
            for msg in round_messages[-10:]
        ])

        # Include prior stance for cumulative awareness
        stance_ctx = ""
        if prior_stance:
            stance_ctx = (
                f"\n\nYOUR PREVIOUS STANCE:\n{prior_stance}\n\n"
                "Update your stance based on what happened this round. "
                "Build on your previous position — note what changed."
            )

        messages = [
            LLMMessage(role="system", content=self.state.persona_prompt),
            LLMMessage(
                role="user",
                content=(
                    "Based on this round's conversation, summarize your "
                    "current stance/position (2-3 sentences). Be specific "
                    "about what you support or oppose and why."
                    f"{stance_ctx}"
                    f"\n\nCONVERSATION:\n{conversation}"
                ),
            ),
        ]

        for attempt in range(max_retries + 1):
            try:
                response = await self._throttled_generate(
                    messages=messages,
                    temperature=0.5,
                    max_tokens=200,
                    round_number=round_number,
                    task_type="stance",
                )

                cleaned = sanitize_llm_response(response.content)
                if cleaned and not cleaned.startswith("[HALLUCINATION_DETECTED"):
                    self.state.current_stance = cleaned
                    logger.debug(
                        "Updated stance for %s (round %d, attempt %d): %s",
                        self.name,
                        round_number,
                        attempt + 1,
                        cleaned[:80],
                    )
                    return

                logger.warning(
                    "Empty/hallucinated stance for %s (round %d, attempt %d)",
                    self.name,
                    round_number,
                    attempt + 1,
                )

            except Exception as e:
                logger.error(
                    "Failed to update stance for %s (round %d, attempt %d): %s",
                    self.name,
                    round_number,
                    attempt + 1,
                    e,
                )

        # All retries exhausted — preserve prior stance rather than blanking
        if not self.state.current_stance and prior_stance:
            self.state.current_stance = prior_stance
            logger.warning(
                "Stance update failed for %s after %d attempts; "
                "preserving prior stance",
                self.name,
                max_retries + 1,
            )

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
