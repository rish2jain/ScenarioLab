"""FastAPI router for voice chat endpoints."""

import logging
import uuid
from io import BytesIO

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.llm.database import VoiceRepository, init_llm_tables
from app.simulation.voice_chat import voice_chat_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/simulations", tags=["voice"])


# In-memory conversation history storage
_conversation_histories: dict[str, list[dict]] = {}
_agent_prompts: dict[str, str] = {}

# Repository instance
_voice_repo = VoiceRepository()
_initialized = False


async def _ensure_initialized():
    """Ensure tables are initialized."""
    global _initialized
    if not _initialized:
        try:
            await init_llm_tables()
            _initialized = True
        except Exception as e:
            logger.warning(f"Failed to init LLM tables: {e}")


class TranscribeResponse(BaseModel):
    """Response from audio transcription."""

    text: str


class SynthesizeRequest(BaseModel):
    """Request for speech synthesis."""

    text: str
    voice: str | None = None


class ConversationResponse(BaseModel):
    """Response from voice conversation."""

    transcript: str
    response_text: str
    audio_url: str


@router.post(
    "/{simulation_id}/voice/transcribe",
    response_model=TranscribeResponse,
)
async def transcribe_audio(
    simulation_id: str,
    audio: UploadFile = File(...),
) -> TranscribeResponse:
    """Transcribe audio file to text using Whisper.

    Args:
        simulation_id: The simulation ID
        audio: Audio file (mp3, mp4, mpeg, m4a, wav, webm)

    Returns:
        Transcribed text
    """
    try:
        audio_data = await audio.read()
        text = await voice_chat_manager.transcribe_audio(audio_data)
        return TranscribeResponse(text=text)
    except Exception as e:
        logger.error(f"Transcription failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Transcription failed: {str(e)}",
        )


@router.post("/{simulation_id}/voice/synthesize")
async def synthesize_speech(
    simulation_id: str,
    request: SynthesizeRequest,
) -> StreamingResponse:
    """Synthesize speech from text using TTS.

    Args:
        simulation_id: The simulation ID
        request: Text and optional voice selection

    Returns:
        Audio file (mp3 format)
    """
    try:
        audio_bytes = await voice_chat_manager.synthesize_speech(
            text=request.text,
            voice=request.voice,
        )
        return StreamingResponse(
            BytesIO(audio_bytes),
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": "attachment; filename=speech.mp3"
            },
        )
    except Exception as e:
        logger.error(f"Speech synthesis failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Speech synthesis failed: {str(e)}",
        )


@router.post(
    "/{simulation_id}/voice/conversation",
    response_model=ConversationResponse,
)
async def voice_conversation(
    simulation_id: str,
    audio: UploadFile = File(...),
    agent_id: str = Form(...),
    agent_persona_prompt: str | None = Form(None),
) -> ConversationResponse:
    """Process a voice conversation turn with an agent.

    Args:
        simulation_id: The simulation ID
        audio: User's audio input
        agent_id: The agent ID to respond
        agent_persona_prompt: Optional agent persona prompt

    Returns:
        Transcript, agent response text, and audio URL
    """
    try:
        # Get or store agent persona prompt
        prompt_key = f"{simulation_id}:{agent_id}"
        if agent_persona_prompt:
            _agent_prompts[prompt_key] = agent_persona_prompt
        persona_prompt = _agent_prompts.get(
            prompt_key,
            "You are a helpful AI assistant.",
        )

        # Get conversation history (try in-memory, then DB)
        history = _conversation_histories.get(prompt_key, [])
        if not history:
            try:
                await _ensure_initialized()
                db_history = await _voice_repo.get_conversation(
                    simulation_id, agent_id
                )
                if db_history:
                    history = db_history
            except Exception as e:
                logger.warning(f"Failed to get conversation from DB: {e}")

        # Read audio data
        audio_data = await audio.read()

        # Process conversation turn
        result = await voice_chat_manager.voice_conversation(
            simulation_id=simulation_id,
            agent_id=agent_id,
            audio_data=audio_data,
            agent_persona_prompt=persona_prompt,
            conversation_history=history,
        )

        # Update conversation history
        history.append({"is_user": True, "content": result["transcript"]})
        history.append({"is_user": False, "content": result["agent_response"]})
        _conversation_histories[prompt_key] = history

        # Persist conversation to DB
        try:
            await _ensure_initialized()
            await _voice_repo.save_conversation(
                simulation_id, agent_id, history
            )
        except Exception as e:
            logger.warning(f"Failed to persist conversation: {e}")

        # Store audio for retrieval
        audio_id = str(uuid.uuid4())
        _audio_storage[audio_id] = result["audio_response"]

        # Persist audio to DB
        try:
            await _ensure_initialized()
            await _voice_repo.save_audio(
                audio_id,
                simulation_id,
                agent_id,
                result["audio_response"],
            )
        except Exception as e:
            logger.warning(f"Failed to persist audio: {e}")

        return ConversationResponse(
            transcript=result["transcript"],
            response_text=result["agent_response"],
            audio_url=(
                f"/api/simulations/{simulation_id}/voice/audio/{audio_id}"
            ),
        )
    except Exception as e:
        logger.error(f"Voice conversation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Voice conversation failed: {str(e)}",
        )


# In-memory audio storage for retrieval
_audio_storage: dict[str, bytes] = {}


@router.get("/{simulation_id}/voice/audio/{audio_id}")
async def get_audio(
    simulation_id: str,
    audio_id: str,
) -> StreamingResponse:
    """Retrieve a previously generated audio file.

    Args:
        simulation_id: The simulation ID
        audio_id: The audio file ID

    Returns:
        Audio file (mp3 format)
    """
    # Try in-memory first
    audio_bytes = _audio_storage.get(audio_id)

    # Fall back to DB
    if not audio_bytes:
        try:
            await _ensure_initialized()
            audio_bytes = await _voice_repo.get_audio(audio_id)
            if audio_bytes:
                _audio_storage[audio_id] = audio_bytes
        except Exception as e:
            logger.warning(f"Failed to get audio from DB: {e}")

    if not audio_bytes:
        raise HTTPException(
            status_code=404,
            detail="Audio not found",
        )

    return StreamingResponse(
        BytesIO(audio_bytes),
        media_type="audio/mpeg",
        headers={
            "Content-Disposition": f"attachment; filename={audio_id}.mp3"
        },
    )


@router.delete("/{simulation_id}/voice/history")
async def clear_conversation_history(
    simulation_id: str,
    agent_id: str | None = None,
) -> dict:
    """Clear conversation history for a simulation or specific agent.

    Args:
        simulation_id: The simulation ID
        agent_id: Optional agent ID to clear history for

    Returns:
        Success status
    """
    if agent_id:
        key = f"{simulation_id}:{agent_id}"
        _conversation_histories.pop(key, None)
        _agent_prompts.pop(key, None)
        # Also clear from DB
        try:
            await _ensure_initialized()
            await _voice_repo.delete_conversation(simulation_id, agent_id)
            await _voice_repo.delete_audio_for_simulation(
                simulation_id, agent_id
            )
        except Exception as e:
            logger.warning(f"Failed to clear conversation from DB: {e}")
    else:
        # Clear all for this simulation
        keys_to_remove = [
            k
            for k in _conversation_histories
            if k.startswith(f"{simulation_id}:")
        ]
        for key in keys_to_remove:
            _conversation_histories.pop(key, None)
            _agent_prompts.pop(key, None)
        # Also clear from DB
        try:
            await _ensure_initialized()
            await _voice_repo.delete_conversation(simulation_id)
            await _voice_repo.delete_audio_for_simulation(simulation_id)
        except Exception as e:
            logger.warning(f"Failed to clear conversations from DB: {e}")

    return {"status": "cleared"}
