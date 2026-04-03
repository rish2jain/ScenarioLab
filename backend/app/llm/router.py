"""LLM API router."""

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import settings
from app.llm.factory import get_llm_provider
from app.llm.fine_tuning import (
    DatasetInfo,
    FineTuningJob,
    LoRAAdapter,
    fine_tuning_manager,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/llm", tags=["llm"])


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


@router.post("/test", response_model=TestConnectionResponse)
async def test_llm_connection():
    """Test LLM connectivity.

    Returns provider info and test result.
    """
    try:
        provider = get_llm_provider()
        test_result = await provider.test_connection()

        return TestConnectionResponse(
            provider=settings.llm_provider,
            model=settings.llm_model_name,
            base_url=settings.llm_base_url,
            status=test_result.get("status", "unknown"),
            message=test_result.get("message", "No message"),
        )
    except Exception as e:
        logger.error(f"Failed to test LLM connection: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to test LLM connection: {str(e)}",
        )


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

    return LLMConfigResponse(
        provider=settings.llm_provider,
        model=settings.llm_model_name,
        base_url=base_url,
    )


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
        logger.error(f"Failed to prepare dataset: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to prepare dataset: {str(e)}",
        )


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
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to start fine-tuning: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start fine-tuning: {str(e)}",
        )


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
    return fine_tuning_manager.list_adapters()


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
        logger.error(f"Failed to create benchmark: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create benchmark: {str(e)}",
        )
