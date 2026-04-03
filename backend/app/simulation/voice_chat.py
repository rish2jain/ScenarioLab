"""Voice chat manager for audio transcription and synthesis."""

import logging
import tempfile
from pathlib import Path

from openai import AsyncOpenAI

from app.config import settings
from app.llm.factory import get_llm_provider
from app.llm.provider import LLMMessage

logger = logging.getLogger(__name__)


class VoiceChatManager:
    """Manages voice interactions with simulation agents."""

    def __init__(self):
        self._client: AsyncOpenAI | None = None

    def _get_client(self) -> AsyncOpenAI:
        """Get or create the OpenAI client."""
        if self._client is None:
            self._client = AsyncOpenAI(api_key=settings.llm_api_key)
        return self._client

    async def transcribe_audio(
        self,
        audio_data: bytes,
        model: str | None = None,
    ) -> str:
        """Transcribe audio using OpenAI Whisper API.

        Args:
            audio_data: Raw audio bytes (mp3, mp4, mpeg, m4a, wav, webm)
            model: Whisper model to use (default: settings.whisper_model)

        Returns:
            Transcribed text
        """
        client = self._get_client()
        model = model or settings.whisper_model

        try:
            # Create a temporary file for the audio data
            with tempfile.NamedTemporaryFile(
                delete=False,
                suffix=".webm",
            ) as temp_file:
                temp_file.write(audio_data)
                temp_path = Path(temp_file.name)

            # Open and transcribe
            with open(temp_path, "rb") as audio_file:
                transcript = await client.audio.transcriptions.create(
                    model=model,
                    file=audio_file,
                )

            # Clean up temp file
            temp_path.unlink(missing_ok=True)

            return transcript.text

        except Exception as e:
            logger.error(f"Failed to transcribe audio: {e}")
            raise RuntimeError(f"Transcription failed: {str(e)}") from e

    async def synthesize_speech(
        self,
        text: str,
        voice: str | None = None,
        model: str | None = None,
    ) -> bytes:
        """Synthesize speech using OpenAI TTS API.

        Args:
            text: Text to convert to speech
            voice: Voice to use (defaults to settings.tts_voice)
            model: TTS model to use (defaults to settings.tts_model)

        Returns:
            Audio bytes (mp3 format)
        """
        client = self._get_client()
        voice = voice or settings.tts_voice
        model = model or settings.tts_model

        try:
            response = await client.audio.speech.create(
                model=model,
                voice=voice,
                input=text,
            )

            # Get audio bytes
            audio_bytes = await response.aread()
            return audio_bytes

        except Exception as e:
            logger.error(f"Failed to synthesize speech: {e}")
            raise RuntimeError(f"Speech synthesis failed: {str(e)}") from e

    async def voice_conversation(
        self,
        simulation_id: str,
        agent_id: str,
        audio_data: bytes,
        agent_persona_prompt: str,
        conversation_history: list[dict] | None = None,
    ) -> dict:
        """Process voice turn: transcribe -> respond -> synthesize.

        Args:
            simulation_id: The simulation ID
            agent_id: The agent ID to respond
            audio_data: User's audio input
            agent_persona_prompt: The agent's system prompt
            conversation_history: Previous conversation messages

        Returns:
            Dictionary with transcript, agent_response, and audio_response
        """
        try:
            # 1. Transcribe user audio
            transcript = await self.transcribe_audio(audio_data)
            logger.info(
                f"Transcribed audio for simulation {simulation_id}: "
                f"{transcript[:50]}..."
            )

            # 2. Get agent response via LLM
            llm_provider = get_llm_provider()

            messages = [
                LLMMessage(role="system", content=agent_persona_prompt)
            ]

            # Add conversation history
            if conversation_history:
                for msg in conversation_history[-10:]:  # Last 10 messages
                    role = "user" if msg.get("is_user") else "assistant"
                    messages.append(
                        LLMMessage(role=role, content=msg.get("content", ""))
                    )

            # Add current user message
            messages.append(LLMMessage(role="user", content=transcript))

            response = await llm_provider.generate(
                messages=messages,
                temperature=0.7,
                max_tokens=1024,
            )

            agent_response = response.content.strip()
            logger.info(
                f"Agent {agent_id} responded: {agent_response[:50]}..."
            )

            # 3. Synthesize agent response
            audio_response = await self.synthesize_speech(agent_response)

            return {
                "transcript": transcript,
                "agent_response": agent_response,
                "audio_response": audio_response,
            }

        except Exception as e:
            logger.error(f"Voice conversation failed: {e}")
            raise RuntimeError(f"Voice conversation failed: {str(e)}") from e


# Global instance
voice_chat_manager = VoiceChatManager()
