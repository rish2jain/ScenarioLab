"""Counterpart Agent Manager for rehearsal simulations."""

import asyncio
import logging
import uuid
from typing import Any

from pydantic import BaseModel, Field

from app.api_integrations.database import (
    counterpart_repo,
    ensure_tables,
)
from app.llm.factory import get_llm_provider
from app.llm.provider import LLMMessage

logger = logging.getLogger(__name__)


REHEARSAL_MODE_TEMPERATURE = {
    "friendly": 0.3,
    "challenging": 0.6,
    "hostile": 0.8,
}


class Objection(BaseModel):
    """An objection from the counterpart agent."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    text: str
    severity: str  # mild, moderate, strong
    category: str  # strategic, financial, operational, political
    suggested_response: str


class RehearsalResponse(BaseModel):
    """Response from a rehearsal turn."""

    response: str
    tone: str
    objection_count: int
    coaching_tips: list[str]


class RehearsalFeedback(BaseModel):
    """Summary feedback from a rehearsal session."""

    overall_rating: float = Field(..., ge=0.0, le=10.0)
    strengths: list[str]
    areas_for_improvement: list[str]
    key_objections_raised: list[str]
    preparation_tips: list[str]


class CounterpartConfig(BaseModel):
    """Configuration for a counterpart agent."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    role: str
    persona_prompt: str
    mode: str = "challenging"
    stakeholder_type: str
    created_from_brief: str = ""


class CounterpartAgentManager:
    """Manages counterpart agents for rehearsal simulations."""

    def __init__(self):
        self._counterparts: dict[str, CounterpartConfig] = {}
        self._conversation_histories: dict[str, list[dict]] = {}
        self._objections_raised: dict[str, list[Objection]] = {}
        self._initialized = False
        self._init_lock = asyncio.Lock()

    async def _ensure_loaded(self) -> None:
        """Ensure counterparts are loaded from database."""
        if self._initialized:
            return
        async with self._init_lock:
            if self._initialized:
                return
            try:
                await ensure_tables()
                counterparts = await counterpart_repo.list_all()
                for cp_data in counterparts:
                    counterpart = CounterpartConfig(
                        id=cp_data["id"],
                        name=cp_data["name"],
                        role=cp_data.get("role", ""),
                        persona_prompt=cp_data.get("persona_data", {}).get("persona_prompt", ""),
                        mode=cp_data["mode"],
                        stakeholder_type=cp_data["stakeholder_type"],
                        created_from_brief=cp_data.get("brief", ""),
                    )
                    self._counterparts[counterpart.id] = counterpart
                    self._conversation_histories[counterpart.id] = cp_data.get("conversation_history", [])
                    self._objections_raised[counterpart.id] = []
                self._initialized = True
                logger.info(f"Loaded {len(self._counterparts)} " f"counterparts from database")
            except Exception as e:
                logger.warning(f"Failed to load counterparts from DB: {e}")

    async def create_counterpart(
        self,
        brief: str,
        stakeholder_type: str,
        rehearsal_mode: str = "challenging",
    ) -> dict[str, Any]:
        """Create a counterpart agent from a brief.

        Args:
            brief: Description of the stakeholder
            stakeholder_type: Type of stakeholder (e.g., "board_member", "investor")
            rehearsal_mode: Mode - friendly, challenging, or hostile

        Returns:
            Counterpart configuration dict
        """
        llm = get_llm_provider()

        # Analyze brief to extract stakeholder profile
        profile_prompt = f"""Analyze the following stakeholder brief and create a detailed persona profile for a rehearsal counterpart.

STAKEHOLDER BRIEF:
{brief}

STAKEHOLDER TYPE: {stakeholder_type}

Create a persona profile with:
1. Name (realistic name for this type of stakeholder)
2. Role (their formal title)
3. Key concerns and motivations
4. Decision-making style
5. Typical objections they might raise
6. Communication style

Respond in JSON format:
{{
    "name": "...",
    "role": "...",
    "concerns": ["..."],
    "decision_style": "...",
    "typical_objections": ["..."],
    "communication_style": "...",
    "system_prompt": "A detailed system prompt for playing this persona in a rehearsal. Should include their background, concerns, decision style, and how they should behave during the rehearsal."
}}"""

        try:
            response = await llm.generate(
                messages=[
                    LLMMessage(
                        role="system",
                        content="You are a persona creation specialist. "
                        "Create realistic stakeholder personas for business rehearsals.",
                    ),
                    LLMMessage(role="user", content=profile_prompt),
                ],
                temperature=0.7,
                max_tokens=1500,
            )

            import json

            content = response.content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

            profile_data = json.loads(content)

            counterpart = CounterpartConfig(
                name=profile_data.get("name", "Counterpart"),
                role=profile_data.get("role", stakeholder_type),
                persona_prompt=profile_data.get(
                    "system_prompt",
                    f"You are a {stakeholder_type} in a business meeting.",
                ),
                mode=rehearsal_mode,
                stakeholder_type=stakeholder_type,
                created_from_brief=brief,
            )

            self._counterparts[counterpart.id] = counterpart
            self._conversation_histories[counterpart.id] = []
            self._objections_raised[counterpart.id] = []

            # Save to database
            await self._save_counterpart(counterpart)

            logger.info(f"Created counterpart {counterpart.id}: {counterpart.name}")

            return {
                "id": counterpart.id,
                "name": counterpart.name,
                "persona": counterpart.persona_prompt,
                "mode": counterpart.mode,
            }

        except Exception as e:
            logger.error(f"Failed to create counterpart: {e}")
            # Create a fallback counterpart
            counterpart = CounterpartConfig(
                name=f"Counterpart {stakeholder_type.title()}",
                role=stakeholder_type,
                persona_prompt=f"You are a {stakeholder_type} in a business meeting. "
                f"Ask probing questions and challenge assumptions.",
                mode=rehearsal_mode,
                stakeholder_type=stakeholder_type,
                created_from_brief=brief,
            )
            self._counterparts[counterpart.id] = counterpart
            self._conversation_histories[counterpart.id] = []
            self._objections_raised[counterpart.id] = []

            # Save to database
            asyncio.create_task(self._save_counterpart(counterpart))

            return {
                "id": counterpart.id,
                "name": counterpart.name,
                "persona": counterpart.persona_prompt,
                "mode": counterpart.mode,
            }

    async def generate_objections(
        self,
        counterpart_id: str,
        presentation_text: str,
    ) -> list[dict[str, Any]]:
        """Generate objections based on presentation content.

        Args:
            counterpart_id: The counterpart ID
            presentation_text: The presentation text to analyze

        Returns:
            List of objections with severity and suggested responses
        """
        counterpart = self._counterparts.get(counterpart_id)
        if not counterpart:
            raise ValueError(f"Counterpart not found: {counterpart_id}")

        llm = get_llm_provider()

        objection_prompt = f"""As {counterpart.name}, a {counterpart.role}, "
"analyze the presentation and generate at least 5 objections.\n

PRESENTATION:
{presentation_text}

YOUR PERSONA:
{counterpart.persona_prompt}

Generate objections in JSON format:
{{
    "objections": [
        {{
            "text": "The objection statement",
            "severity": "mild|moderate|strong",
            "category": "strategic|financial|operational|political",
            "suggested_response": "A suggested way to address this objection"
        }}
    ]
}}

Focus on realistic concerns this stakeholder would have."""

        try:
            response = await llm.generate(
                messages=[
                    LLMMessage(role="system", content=objection_prompt),
                    LLMMessage(
                        role="user",
                        content="Generate your objections.",
                    ),
                ],
                temperature=REHEARSAL_MODE_TEMPERATURE.get(counterpart.mode, 0.6),
                max_tokens=2000,
            )

            import json

            content = response.content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

            data = json.loads(content)
            objections = []

            for obj_data in data.get("objections", []):
                objection = Objection(
                    text=obj_data.get("text", ""),
                    severity=obj_data.get("severity", "moderate"),
                    category=obj_data.get("category", "strategic"),
                    suggested_response=obj_data.get("suggested_response", ""),
                )
                objections.append(objection)

            # Store objections
            if counterpart_id not in self._objections_raised:
                self._objections_raised[counterpart_id] = []
            self._objections_raised[counterpart_id].extend(objections)

            return [obj.model_dump() for obj in objections]

        except Exception as e:
            logger.error(f"Failed to generate objections: {e}")
            # Return fallback objections
            fallback = [
                Objection(
                    text="I have concerns about the timeline.",
                    severity="moderate",
                    category="operational",
                    suggested_response=("Provide a detailed timeline with milestones."),
                ),
                Objection(
                    text="What's the financial impact?",
                    severity="strong",
                    category="financial",
                    suggested_response=("Present ROI analysis and cost breakdown."),
                ),
            ]
            return [obj.model_dump() for obj in fallback]

    async def rehearse(
        self,
        counterpart_id: str,
        user_message: str,
    ) -> dict[str, Any]:
        """Interactive rehearsal turn.

        Args:
            counterpart_id: The counterpart ID
            user_message: The user's message/presentation

        Returns:
            Response with tone, objection count, and coaching tips
        """
        counterpart = self._counterparts.get(counterpart_id)
        if not counterpart:
            raise ValueError(f"Counterpart not found: {counterpart_id}")

        llm = get_llm_provider()

        # Build conversation history
        history = self._conversation_histories.get(counterpart_id, [])

        messages = [
            LLMMessage(role="system", content=counterpart.persona_prompt),
        ]

        # Add mode-specific instructions
        mode_instructions = {
            "friendly": (
                "Be supportive but thorough. Ask clarifying questions. "
                "Help the presenter improve through gentle guidance."
            ),
            "challenging": (
                "Be direct and push back on weak arguments. " "Ask tough questions. Challenge assumptions."
            ),
            "hostile": (
                "Be skeptical and demanding. Push hard on every point. "
                "Express frustration with unclear answers. "
                "Simulate a difficult stakeholder."
            ),
        }

        mode_instruction = mode_instructions.get(counterpart.mode, "")
        messages.append(
            LLMMessage(
                role="system",
                content=f"REHEARSAL MODE: {mode_instruction}",
            )
        )

        # Add conversation history
        for msg in history[-10:]:
            role = "user" if msg.get("is_user") else "assistant"
            messages.append(LLMMessage(role=role, content=msg.get("content", "")))

        # Add current message
        messages.append(LLMMessage(role="user", content=user_message))

        try:
            response = await llm.generate(
                messages=messages,
                temperature=REHEARSAL_MODE_TEMPERATURE.get(counterpart.mode, 0.6),
                max_tokens=1000,
            )

            content = response.content.strip()

            # Update history
            history.append({"is_user": True, "content": user_message})
            history.append({"is_user": False, "content": content})
            self._conversation_histories[counterpart_id] = history

            # Save conversation history to database
            asyncio.create_task(counterpart_repo.save_conversation(counterpart_id, history))

            # Count objections in this response
            objection_keywords = [
                "but",
                "however",
                "concern",
                "issue",
                "problem",
                "disagree",
                "challenge",
                "worry",
                "risk",
                "unclear",
            ]
            objection_count = sum(1 for kw in objection_keywords if kw in content.lower())

            # Generate coaching tips
            coaching_tips = self._generate_coaching_tips(user_message, content, counterpart.mode)

            return {
                "response": content,
                "tone": counterpart.mode,
                "objection_count": objection_count,
                "coaching_tips": coaching_tips,
            }

        except Exception as e:
            logger.error(f"Rehearsal failed: {e}")
            return {
                "response": "I apologize, I'm having trouble responding. " "Please try again.",
                "tone": counterpart.mode,
                "objection_count": 0,
                "coaching_tips": [],
            }

    def _generate_coaching_tips(
        self,
        user_message: str,
        response: str,
        mode: str,
    ) -> list[str]:
        """Generate coaching tips based on the exchange."""
        tips = []

        # Check message length
        if len(user_message) < 50:
            tips.append("Consider providing more detail in your responses.")

        # Check for hedging language
        hedge_words = ["maybe", "possibly", "might", "could be", "i think"]
        if any(word in user_message.lower() for word in hedge_words):
            tips.append("Try to be more confident. Avoid hedging language.")

        # Check for data/numbers
        import re

        if not re.search(r"\d+", user_message):
            tips.append("Support your points with specific data or metrics.")

        # Mode-specific tips
        if mode == "hostile":
            tips.append("Stay calm and address concerns directly. " "Don't get defensive.")

        return tips[:3]  # Return max 3 tips

    async def get_feedback_summary(
        self,
        counterpart_id: str,
    ) -> dict[str, Any]:
        """Get feedback summary for a rehearsal session.

        Args:
            counterpart_id: The counterpart ID

        Returns:
            Feedback summary with ratings and recommendations
        """
        counterpart = self._counterparts.get(counterpart_id)
        if not counterpart:
            raise ValueError(f"Counterpart not found: {counterpart_id}")

        history = self._conversation_histories.get(counterpart_id, [])
        objections = self._objections_raised.get(counterpart_id, [])

        # Calculate rating based on conversation length
        base_rating = min(len(history) / 10, 5) + 3  # 3-8 base
        objection_bonus = min(len(objections) * 0.2, 2)  # bonus
        overall_rating = min(base_rating + objection_bonus, 10)

        # Extract key objections
        key_objections = [obj.text for obj in objections[:5]]

        # Generate feedback
        llm = get_llm_provider()

        conversation_text = "\n".join(
            [f"{'User' if msg.get('is_user') else 'Counterpart'}: " f"{msg.get('content', '')}" for msg in history]
        )

        try:
            obj_text = chr(10).join(f"- {obj}" for obj in key_objections[:3]) if key_objections else "None"
            feedback_prompt = f"""Analyze this rehearsal conversation.

CONVERSATION:
{conversation_text}

OBJECTIONS RAISED:
{obj_text}

Provide feedback in JSON format:
{{
    "strengths": ["strength 1", "strength 2"],
    "areas_for_improvement": ["area 1", "area 2"],
    "preparation_tips": ["tip 1", "tip 2"]
}}"""

            response = await llm.generate(
                messages=[
                    LLMMessage(
                        role="system",
                        content="You are a presentation coach.",
                    ),
                    LLMMessage(role="user", content=feedback_prompt),
                ],
                temperature=0.5,
                max_tokens=1000,
            )

            import json

            content = response.content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

            feedback_data = json.loads(content)

            return {
                "overall_rating": round(overall_rating, 1),
                "strengths": feedback_data.get("strengths", []),
                "areas_for_improvement": feedback_data.get("areas_for_improvement", []),
                "key_objections_raised": key_objections,
                "preparation_tips": feedback_data.get("preparation_tips", []),
            }

        except Exception as e:
            logger.error(f"Failed to generate feedback: {e}")
            return {
                "overall_rating": round(overall_rating, 1),
                "strengths": ["Participated in rehearsal session"],
                "areas_for_improvement": ["Continue practicing"],
                "key_objections_raised": key_objections,
                "preparation_tips": ["Prepare more thoroughly next time"],
            }

    async def get_counterpart(self, counterpart_id: str) -> CounterpartConfig | None:
        """Get a counterpart by ID."""
        await self._ensure_loaded()
        return self._counterparts.get(counterpart_id)

    async def list_counterparts(self) -> list[dict[str, Any]]:
        """List all counterparts."""
        await self._ensure_loaded()
        return [
            {
                "id": c.id,
                "name": c.name,
                "role": c.role,
                "mode": c.mode,
                "stakeholder_type": c.stakeholder_type,
            }
            for c in self._counterparts.values()
        ]

    async def delete_counterpart(self, counterpart_id: str) -> bool:
        """Delete a counterpart."""
        await self._ensure_loaded()
        if counterpart_id in self._counterparts:
            del self._counterparts[counterpart_id]
            self._conversation_histories.pop(counterpart_id, None)
            self._objections_raised.pop(counterpart_id, None)
            # Delete from database (async fire-and-forget)
            asyncio.create_task(counterpart_repo.delete(counterpart_id))
            return True
        return False

    async def _save_counterpart(self, counterpart: CounterpartConfig) -> None:
        """Save counterpart to database."""
        try:
            counterpart_data = {
                "id": counterpart.id,
                "name": counterpart.name,
                "brief": counterpart.created_from_brief,
                "stakeholder_type": counterpart.stakeholder_type,
                "mode": counterpart.mode,
                "persona_data": {
                    "role": counterpart.role,
                    "persona_prompt": counterpart.persona_prompt,
                },
                "conversation_history": self._conversation_histories.get(counterpart.id, []),
            }
            await counterpart_repo.save(counterpart_data)
        except Exception as e:
            logger.warning(f"Failed to save counterpart to DB: {e}")


# Global instance
counterpart_manager = CounterpartAgentManager()
