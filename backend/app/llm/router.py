"""LLM API router."""

import asyncio
import logging
import time

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.config import settings
from app.llm.capabilities_cache import CapabilitiesCache
from app.llm.factory import get_llm_provider, get_local_llm_provider
from app.llm.fine_tuning import (
    DatasetInfo,
    FineTuningJob,
    LoRAAdapter,
    fine_tuning_manager,
)
from app.llm.wizard_models import wizard_model_options

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/llm", tags=["llm"])

_default_capabilities_cache = CapabilitiesCache(ttl_sec=60.0)


def get_capabilities_cache() -> CapabilitiesCache:
    """FastAPI dependency; override in tests via ``app.dependency_overrides``."""
    return _default_capabilities_cache


def _unavailable_capabilities() -> dict:
    """Payload when hybrid/local inference is not available (cached as-is)."""
    return {
        "hybrid_available": False,
        "local_provider": None,
        "local_model": None,
        "default_inference_mode": "cloud",
    }


class TestConnectionResponse(BaseModel):
    """Response for test connection endpoint."""

    provider: str
    model: str
    base_url: str
    status: str
    message: str


class LLMConfigResponse(BaseModel):
    """Response for LLM configuration endpoint."""

    provider: str
    model: str
    base_url: str


class WizardModelItem(BaseModel):
    """One selectable model in the new-simulation wizard."""

    id: str
    name: str
    desc: str = ""


class WizardModelsResponse(BaseModel):
    """Models compatible with the server's configured LLM provider."""

    provider: str
    models: list[WizardModelItem]


class InferenceCapabilitiesResponse(BaseModel):
    """Hybrid inference availability for the simulation wizard."""

    hybrid_available: bool
    local_provider: str | None = None
    local_model: str | None = None
    default_inference_mode: str


@router.post("/test", response_model=TestConnectionResponse)
async def test_llm_connection():
    """Test LLM connectivity.

    Returns provider info and test result.
    """
    try:
        provider = get_llm_provider()
        test_result = await provider.test_connection()
        effective_model = test_result.get("model") or settings.llm_model_name

        return TestConnectionResponse(
            provider=settings.llm_provider,
            model=effective_model,
            base_url=settings.llm_base_url,
            status=test_result.get("status", "unknown"),
            message=test_result.get("message", "No message"),
        )
    except Exception as e:
        logger.exception("Failed to test LLM connection")
        raise HTTPException(
            status_code=500,
            detail="Failed to test LLM connection",
        ) from e


@router.get("/wizard-models", response_model=WizardModelsResponse)
async def get_wizard_models():
    """Return model ids valid for the configured ``LLM_PROVIDER``."""
    try:
        # Anthropic may call GET /v1/models (blocking); run off the event loop.
        raw = await asyncio.to_thread(wizard_model_options)
        models = [WizardModelItem(**m) for m in raw]
        return WizardModelsResponse(
            provider=settings.llm_provider,
            models=models,
        )
    except Exception as e:
        logger.exception("Failed to load wizard models")
        raise HTTPException(
            status_code=500,
            detail="Failed to load wizard models",
        ) from e


@router.get("/config", response_model=LLMConfigResponse)
async def get_llm_config():
    """Get current LLM configuration.

    Returns provider, model, and base_url (without API key).
    """
    # Determine effective base URL
    base_url = settings.llm_base_url
    if not base_url or base_url == "https://api.openai.com/v1":
        # Use provider-specific defaults
        provider_defaults = {
            "openai": "https://api.openai.com/v1",
            "qwen": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "google": "https://generativelanguage.googleapis.com/v1beta",
            "ollama": "http://localhost:11434/v1",
            "llamacpp": "http://localhost:8080/v1",
        }
        base_url = provider_defaults.get(
            settings.llm_provider.lower(),
            settings.llm_base_url,
        )

    provider = get_llm_provider()
    effective_model = getattr(provider, "model", "") or settings.llm_model_name or "provider default"

    return LLMConfigResponse(
        provider=settings.llm_provider,
        model=effective_model,
        base_url=base_url,
    )


@router.get("/capabilities", response_model=InferenceCapabilitiesResponse)
async def get_inference_capabilities(
    cache: CapabilitiesCache = Depends(get_capabilities_cache),
):
    """Probe local LLM (cached per ``cache.ttl_sec``) for hybrid inference toggle."""
    cached_payload = await cache.get_cached()
    if cached_payload is not None:
        return InferenceCapabilitiesResponse(**cached_payload)

    async with cache.lock:
        now = time.monotonic()
        cached_payload = cache.peek_valid(now)
        if cached_payload is not None:
            return InferenceCapabilitiesResponse(**cached_payload)

        default_mode = (settings.inference_mode or "cloud").strip().lower()
        if default_mode not in ("cloud", "hybrid", "local"):
            default_mode = "cloud"

        if not (settings.local_llm_provider or "").strip():
            body = _unavailable_capabilities()
            cache.set_cached_locked(body)
            return InferenceCapabilitiesResponse(**body)

        local = get_local_llm_provider()
        if local is None:
            body = _unavailable_capabilities()
            cache.set_cached_locked(body)
            return InferenceCapabilitiesResponse(**body)

        try:
            await asyncio.wait_for(local.test_connection(), timeout=5.0)
        except Exception as e:
            logger.debug("Local LLM capabilities probe failed: %s", e)
            body = _unavailable_capabilities()
            cache.set_cached_locked(body)
            return InferenceCapabilitiesResponse(**body)

        lp = (settings.local_llm_provider or "").strip().lower()
        lm = (settings.local_llm_model_name or "").strip() or None
        body = {
            "hybrid_available": True,
            "local_provider": lp,
            "local_model": lm,
            "default_inference_mode": "hybrid" if default_mode == "hybrid" else "cloud",
        }
        cache.set_cached_locked(body)
        return InferenceCapabilitiesResponse(**body)


# Fine-tuning endpoints


class PrepareDatasetRequest(BaseModel):
    """Request to prepare a dataset for fine-tuning."""

    data_source: str
    data_type: str  # earnings_calls, sec_filings, regulatory_testimony
    output_format: str = "jsonl"


class StartFineTuningRequest(BaseModel):
    """Request to start a fine-tuning job."""

    dataset_id: str
    base_model: str
    lora_config: dict | None = None


class CreateBenchmarkRequest(BaseModel):
    """Request to create a benchmark."""

    domain: str
    num_questions: int = 20


@router.post(
    "/fine-tune/prepare-dataset",
    response_model=DatasetInfo,
)
async def prepare_dataset(request: PrepareDatasetRequest):
    """Prepare a dataset for fine-tuning.

    Parses raw data and converts into training format.
    """
    try:
        dataset = await fine_tuning_manager.prepare_dataset(
            data_source=request.data_source,
            data_type=request.data_type,
            output_format=request.output_format,
        )
        return dataset
    except Exception as e:
        logger.exception("Failed to prepare dataset")
        raise HTTPException(
            status_code=500,
            detail="Failed to prepare dataset",
        ) from e


@router.post(
    "/fine-tune/start",
    response_model=FineTuningJob,
)
async def start_fine_tuning(request: StartFineTuningRequest):
    """Start a fine-tuning job.

    Creates a fine-tuning job with LoRA/QLoRA configuration.
    """
    try:
        job = await fine_tuning_manager.start_fine_tuning(
            dataset_id=request.dataset_id,
            base_model=request.base_model,
            config=request.lora_config,
        )
        return job
    except ValueError as e:
        logger.exception("Invalid request for fine-tuning")
        raise HTTPException(
            status_code=400,
            detail="Invalid request for fine-tuning",
        ) from e
    except Exception as e:
        logger.exception("Failed to start fine-tuning")
        raise HTTPException(
            status_code=500,
            detail="Failed to start fine-tuning",
        ) from e


@router.get(
    "/fine-tune/status/{job_id}",
    response_model=FineTuningJob,
)
async def get_fine_tune_status(job_id: str):
    """Get the status of a fine-tuning job."""
    try:
        job = fine_tuning_manager.get_job_status(job_id)
        return job
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/fine-tune/adapters", response_model=list[LoRAAdapter])
async def list_adapters():
    """List all available LoRA adapters."""
    return await fine_tuning_manager.list_adapters()


@router.get("/fine-tune/jobs", response_model=list[FineTuningJob])
async def list_fine_tuning_jobs():
    """List all fine-tuning jobs."""
    return await fine_tuning_manager.list_jobs()


@router.post(
    "/fine-tune/activate/{adapter_id}",
    response_model=LoRAAdapter,
)
async def activate_adapter(adapter_id: str):
    """Activate a LoRA adapter for simulation agent inference."""
    try:
        adapter = fine_tuning_manager.activate_adapter(adapter_id)
        return adapter
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/fine-tune/benchmark")
async def create_benchmark(request: CreateBenchmarkRequest):
    """Create a domain-specific benchmark for evaluation."""
    try:
        benchmark = await fine_tuning_manager.create_benchmark(
            domain=request.domain,
            num_questions=request.num_questions,
        )
        return benchmark
    except Exception as e:
        logger.exception("Failed to create benchmark")
        raise HTTPException(
            status_code=500,
            detail="Failed to create benchmark",
        ) from e
