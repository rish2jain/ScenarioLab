"""Fine-tuning management for domain-specific LLM agents.

This module provides a management layer for LoRA/QLoRA fine-tuning pipelines.
Actual training requires GPU hardware - this implementation provides the
orchestration and configuration management.
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.llm.database import FineTuningRepository, init_llm_tables
from app.llm.factory import get_llm_provider
from app.llm.provider import LLMMessage

logger = logging.getLogger(__name__)

# Cap parallel dataset lookups in list_jobs (each may hit the repository).
_MAX_CONCURRENT_DATASET_LOOKUPS = 8


# Pydantic models for fine-tuning


class LoRAConfig(BaseModel):
    """LoRA configuration for fine-tuning."""

    r: int = 16
    lora_alpha: int = 32
    lora_dropout: float = 0.05
    target_modules: list[str] = ["q_proj", "v_proj", "k_proj", "o_proj"]
    bias: str = "none"
    task_type: str = "CAUSAL_LM"


class FineTuningJob(BaseModel):
    """A fine-tuning job entry."""

    job_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    dataset_id: str
    base_model: str
    lora_config: LoRAConfig = LoRAConfig()
    status: str = "queued"  # queued, training, completed, failed
    progress: float = 0.0
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    completed_at: str | None = None
    metrics: dict[str, Any] = {}
    error_message: str | None = None
    num_examples: int | None = None
    hyperparameters: dict[str, Any] = {
        "learning_rate": 2e-4,
        "num_train_epochs": 3,
        "per_device_train_batch_size": 4,
        "gradient_accumulation_steps": 4,
        "warmup_steps": 100,
        "logging_steps": 10,
        "save_steps": 500,
    }


class LoRAAdapter(BaseModel):
    """A trained LoRA adapter."""

    adapter_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    job_id: str
    base_model: str
    domain: str
    size_mb: float = 0.0
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    performance_metrics: dict[str, Any] = {}
    active: bool = False


class DatasetInfo(BaseModel):
    """Information about a prepared dataset."""

    dataset_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    data_type: str  # earnings_calls, sec_filings, regulatory_testimony
    num_examples: int = 0
    format: str = "jsonl"
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    preview_samples: list[dict[str, str]] = []


class BenchmarkInfo(BaseModel):
    """Information about a benchmark dataset."""

    benchmark_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    domain: str
    questions: list[dict[str, Any]]
    evaluation_criteria: list[str]
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class FineTuningManager:
    """Manages fine-tuning jobs, datasets, and adapters.

    This class provides the management layer for fine-tuning operations.
    In production, it would interface with training infrastructure
    (e.g., transformers, peft, accelerate) for actual GPU training.

    For now, it simulates the pipeline and provides the orchestration layer.
    """

    def __init__(self):
        self._jobs: dict[str, FineTuningJob] = {}
        self._datasets: dict[str, DatasetInfo] = {}
        self._adapters: dict[str, LoRAAdapter] = {}
        self._benchmarks: dict[str, BenchmarkInfo] = {}
        self._active_adapter_id: str | None = None
        self._repo = FineTuningRepository()
        self._initialized = False

    async def _ensure_initialized(self):
        """Ensure tables are initialized."""
        if not self._initialized:
            try:
                await init_llm_tables()
                self._initialized = True
            except Exception as e:
                logger.warning(f"Failed to init LLM tables: {e}")

    async def _with_dataset_examples(self, job: FineTuningJob) -> FineTuningJob:
        """Attach dataset example count when missing (e.g. job loaded from DB)."""
        if job.num_examples is not None:
            return job
        try:
            dataset = await self.get_dataset(job.dataset_id)
            return job.model_copy(update={"num_examples": dataset.num_examples})
        except Exception as e:
            logger.debug(
                "Failed to enrich job with num_examples from dataset (dataset_id=%s): %s",
                job.dataset_id,
                e,
            )
            return job

    async def prepare_dataset(
        self,
        data_source: str,
        data_type: str,
        output_format: str = "jsonl",
    ) -> DatasetInfo:
        """Prepare a dataset for fine-tuning.

        Parses raw data (earnings calls, SEC filings, regulatory testimony)
        and converts it into training format (instruction/response pairs).

        Args:
            data_source: Raw data content or file path
            data_type: Type of data (earnings_calls, sec_filings,
                regulatory_testimony)
            output_format: Output format (default: jsonl)

        Returns:
            DatasetInfo with dataset_id, num_examples, format, preview_samples
        """
        logger.info(f"Preparing dataset of type {data_type}")

        try:
            llm = get_llm_provider()

            # Build prompt based on data type
            type_instructions = {
                "earnings_calls": (
                    "Convert earnings call transcripts into Q&A pairs "
                    "focusing on strategic decisions, financial guidance, "
                    "and executive sentiment."
                ),
                "sec_filings": (
                    "Convert SEC filing sections into Q&A pairs "
                    "focusing on risk factors, management discussion, "
                    "and financial statements."
                ),
                "regulatory_testimony": (
                    "Convert regulatory testimony into Q&A pairs "
                    "focusing on compliance positions, regulatory concerns, "
                    "and industry perspectives."
                ),
            }

            instruction = type_instructions.get(
                data_type,
                "Convert the document into instruction/response pairs " "suitable for fine-tuning.",
            )

            prompt = f"""You are a data preparation assistant. {instruction}

RAW DATA:
{data_source[:8000]}

TASK:
Convert this into training examples in JSONL format. Each line should be:
{{"instruction": "...", "input": "...", "output": "..."}}

Create 3-5 high-quality examples that capture key strategic insights.

Respond with a JSON array of examples:
{{
    "examples": [
        {{
            "instruction": "What strategic decision was made?",
            "input": "Context from the document",
            "output": "The strategic decision was..."
        }}
    ]
}}"""

            response = await llm.generate(
                messages=[
                    LLMMessage(
                        role="system",
                        content="You are a data preparation expert. " "Respond with valid JSON only.",
                    ),
                    LLMMessage(role="user", content=prompt),
                ],
                temperature=0.3,
                max_tokens=2000,
            )

            # Parse response
            content = response.content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

            data = json.loads(content)
            examples = data.get("examples", [])

            # Create dataset info
            dataset = DatasetInfo(
                data_type=data_type,
                num_examples=len(examples),
                format=output_format,
                preview_samples=examples[:3],
            )

            # Store dataset
            self._datasets[dataset.dataset_id] = dataset

            # Persist to DB
            try:
                await self._ensure_initialized()
                await self._repo.save_dataset(dataset.model_dump())
            except Exception as e:
                logger.warning(f"Failed to persist dataset: {e}")

            logger.info(f"Created dataset {dataset.dataset_id} " f"with {dataset.num_examples} examples")
            return dataset

        except Exception as e:
            logger.error(f"Error preparing dataset: {e}")
            # Return empty dataset on error
            dataset = DatasetInfo(
                data_type=data_type,
                num_examples=0,
                format=output_format,
            )
            self._datasets[dataset.dataset_id] = dataset
            try:
                await self._ensure_initialized()
                await self._repo.save_dataset(dataset.model_dump())
            except Exception as persist_err:
                logger.warning(f"Failed to persist dataset: {persist_err}")
            return dataset

    async def start_fine_tuning(
        self,
        dataset_id: str,
        base_model: str,
        config: dict[str, Any] | None = None,
    ) -> FineTuningJob:
        """Start a fine-tuning job.

        Creates a fine-tuning job with LoRA/QLoRA configuration.
        In production, this would launch actual training on GPU infrastructure.

        Args:
            dataset_id: ID of prepared dataset
            base_model: Base model to fine-tune (e.g., "llama-2-7b")
            config: Optional LoRA configuration overrides

        Returns:
            FineTuningJob with job_id and configuration
        """
        # Verify dataset exists
        dataset = self._datasets.get(dataset_id)
        if not dataset:
            raise ValueError(f"Dataset not found: {dataset_id}")

        # Create LoRA config with overrides
        lora_config = LoRAConfig()
        if config:
            for key, value in config.items():
                if hasattr(lora_config, key):
                    setattr(lora_config, key, value)

        # Create job
        job = FineTuningJob(
            dataset_id=dataset_id,
            base_model=base_model,
            lora_config=lora_config,
            num_examples=dataset.num_examples,
        )

        if config and "hyperparameters" in config:
            job.hyperparameters.update(config["hyperparameters"])

        # Store job
        self._jobs[job.job_id] = job

        # Persist to DB
        try:
            await self._ensure_initialized()
            await self._repo.save_job(job.model_dump())
        except Exception as e:
            logger.warning(f"Failed to persist job: {e}")

        logger.info(f"Created fine-tuning job {job.job_id} " f"for model {base_model}")

        # In production, would launch training here
        # For now, simulate completion after a delay would be handled
        # by a background task in a real implementation

        return job

    async def get_job_status(self, job_id: str) -> FineTuningJob:
        """Get the status of a fine-tuning job.

        Args:
            job_id: ID of the job to check

        Returns:
            FineTuningJob with current status, progress, and metrics

        Raises:
            ValueError: If job not found
        """
        # Try in-memory first
        job = self._jobs.get(job_id)
        if job:
            return await self._with_dataset_examples(job)

        # Fall back to DB
        try:
            await self._ensure_initialized()
            job_data = await self._repo.get_job(job_id)
            if job_data:
                job = FineTuningJob(**job_data)
                self._jobs[job_id] = job
                return await self._with_dataset_examples(job)
        except Exception as e:
            logger.warning(f"Failed to get job from DB: {e}")

        raise ValueError(f"Job not found: {job_id}")

    async def list_adapters(self) -> list[LoRAAdapter]:
        """List all available LoRA adapters.

        Returns:
            List of LoRAAdapter with metadata
        """
        # Try DB first, then merge with in-memory
        try:
            await self._ensure_initialized()
            adapters_data = await self._repo.list_adapters()
            for adapter_data in adapters_data:
                adapter_id = adapter_data["adapter_id"]
                if adapter_id not in self._adapters:
                    self._adapters[adapter_id] = LoRAAdapter(**adapter_data)
        except Exception as e:
            logger.warning(f"Failed to list adapters from DB: {e}")

        return list(self._adapters.values())

    async def activate_adapter(self, adapter_id: str) -> LoRAAdapter:
        """Activate a LoRA adapter for simulation agent inference.

        Args:
            adapter_id: ID of adapter to activate

        Returns:
            The activated LoRAAdapter

        Raises:
            ValueError: If adapter not found
        """
        adapter = self._adapters.get(adapter_id)
        if not adapter:
            raise ValueError(f"Adapter not found: {adapter_id}")

        # Deactivate all others
        for a in self._adapters.values():
            a.active = False

        # Activate this one
        adapter.active = True
        self._active_adapter_id = adapter_id

        # Persist to DB
        try:
            await self._ensure_initialized()
            await self._repo.set_active_adapter(adapter_id)
            await self._repo.save_adapter(adapter.model_dump())
        except Exception as e:
            logger.warning(f"Failed to persist adapter activation: {e}")

        logger.info(f"Activated adapter {adapter_id}")
        return adapter

    async def get_active_adapter(self) -> LoRAAdapter | None:
        """Get the currently active adapter.

        Returns:
            Active LoRAAdapter or None
        """
        # Try in-memory first
        if self._active_adapter_id:
            return self._adapters.get(self._active_adapter_id)

        # Fall back to DB
        try:
            await self._ensure_initialized()
            adapter_data = await self._repo.get_active_adapter()
            if adapter_data:
                adapter = LoRAAdapter(**adapter_data)
                self._adapters[adapter.adapter_id] = adapter
                self._active_adapter_id = adapter.adapter_id
                return adapter
        except Exception as e:
            logger.warning(f"Failed to get active adapter from DB: {e}")

        return None

    async def simulate_job_completion(
        self,
        job_id: str,
        success: bool = True,
        metrics: dict[str, Any] | None = None,
    ) -> LoRAAdapter:
        """Simulate job completion (for testing/demo purposes).

        In production, this would be called by the training pipeline
        upon actual completion.

        Args:
            job_id: ID of job to complete
            success: Whether job succeeded
            metrics: Optional training metrics

        Returns:
            Created LoRAAdapter if successful

        Raises:
            ValueError: If job not found
        """
        job = self._jobs.get(job_id)
        if not job:
            raise ValueError(f"Job not found: {job_id}")

        if success:
            job.status = "completed"
            job.progress = 1.0
            job.completed_at = datetime.utcnow().isoformat()
            if metrics:
                job.metrics = metrics

            # Create adapter
            adapter = LoRAAdapter(
                job_id=job_id,
                base_model=job.base_model,
                domain=self._datasets.get(job.dataset_id, DatasetInfo()).data_type,
                size_mb=256.0,  # Simulated size
                performance_metrics=metrics or {"loss": 0.5, "accuracy": 0.85},
            )

            self._adapters[adapter.adapter_id] = adapter

            # Persist to DB
            try:
                await self._ensure_initialized()
                await self._repo.save_adapter(adapter.model_dump())
                await self._repo.save_job(job.model_dump())
            except Exception as e:
                logger.warning(f"Failed to persist adapter/job: {e}")

            logger.info(f"Job {job_id} completed, created adapter {adapter.adapter_id}")
            return adapter
        else:
            job.status = "failed"
            job.error_message = "Simulated failure"
            job.completed_at = datetime.utcnow().isoformat()

            # Persist to DB
            try:
                await self._ensure_initialized()
                await self._repo.save_job(job.model_dump())
            except Exception as e:
                logger.warning(f"Failed to persist failed job: {e}")

            logger.warning(f"Job {job_id} failed")
            raise RuntimeError(f"Job {job_id} failed")

    async def create_benchmark(
        self,
        domain: str,
        num_questions: int = 20,
    ) -> BenchmarkInfo:
        """Create a domain-specific benchmark for evaluation.

        Generates benchmark questions via LLM for evaluating
        fine-tuned models.

        Args:
            domain: Domain for benchmark (e.g., "healthcare_strategy")
            num_questions: Number of questions to generate

        Returns:
            BenchmarkInfo with benchmark_id, domain, questions,
                evaluation_criteria
        """
        logger.info(f"Creating benchmark for {domain}")

        try:
            llm = get_llm_provider()

            prompt = f"""You are a benchmark creation assistant.
Create {num_questions} domain-specific evaluation questions
for testing a strategy consultant AI model.

DOMAIN: {domain}

TASK:
Create challenging questions that test:
1. Domain knowledge
2. Strategic thinking
3. Stakeholder analysis
4. Risk assessment
5. Decision-making under uncertainty

Respond with valid JSON:
{{
    "questions": [
        {{
            "id": 1,
            "question": "The question text",
            "context": "Context or scenario",
            "type": "analysis|recommendation|evaluation",
            "difficulty": "easy|medium|hard"
        }}
    ],
    "evaluation_criteria": [
        "Accuracy of domain knowledge",
        "Quality of strategic reasoning",
        ...
    ]
}}"""

            response = await llm.generate(
                messages=[
                    LLMMessage(
                        role="system",
                        content="You are a benchmark creation expert. " "Respond with valid JSON only.",
                    ),
                    LLMMessage(role="user", content=prompt),
                ],
                temperature=0.5,
                max_tokens=3000,
            )

            # Parse response
            content = response.content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

            data = json.loads(content)

            benchmark = BenchmarkInfo(
                domain=domain,
                questions=data.get("questions", [])[:num_questions],
                evaluation_criteria=data.get("evaluation_criteria", []),
            )

            self._benchmarks[benchmark.benchmark_id] = benchmark

            # Persist to DB
            try:
                await self._ensure_initialized()
                await self._repo.save_benchmark(benchmark.model_dump())
            except Exception as persist_err:
                logger.warning(f"Failed to persist benchmark: {persist_err}")

            logger.info(f"Created benchmark {benchmark.benchmark_id} " f"with {len(benchmark.questions)} questions")
            return benchmark

        except Exception as e:
            logger.error(f"Error creating benchmark: {e}")
            # Return minimal benchmark
            benchmark = BenchmarkInfo(
                domain=domain,
                questions=[],
                evaluation_criteria=["Accuracy", "Relevance", "Depth"],
            )
            self._benchmarks[benchmark.benchmark_id] = benchmark
            try:
                await self._ensure_initialized()
                await self._repo.save_benchmark(benchmark.model_dump())
            except Exception as persist_err:
                logger.warning(f"Failed to persist benchmark: {persist_err}")
            return benchmark

    async def list_jobs(self) -> list[FineTuningJob]:
        """List all fine-tuning jobs.

        Returns:
            List of all FineTuningJob entries
        """
        # Try DB first, then merge with in-memory
        try:
            await self._ensure_initialized()
            jobs_data = await self._repo.list_jobs()
            for job_data in jobs_data:
                job_id = job_data["job_id"]
                if job_id not in self._jobs:
                    self._jobs[job_id] = FineTuningJob(**job_data)
        except Exception as e:
            logger.warning(f"Failed to list jobs from DB: {e}")

        jobs = list(self._jobs.values())
        if not jobs:
            return []
        sem = asyncio.Semaphore(_MAX_CONCURRENT_DATASET_LOOKUPS)

        async def _with_sem(j: FineTuningJob) -> FineTuningJob:
            async with sem:
                return await self._with_dataset_examples(j)

        return list(await asyncio.gather(*(_with_sem(j) for j in jobs)))

    async def list_datasets(self) -> list[DatasetInfo]:
        """List all prepared datasets.

        Returns:
            List of all DatasetInfo entries
        """
        # Try DB first, then merge with in-memory
        try:
            await self._ensure_initialized()
            datasets_data = await self._repo.list_datasets()
            for dataset_data in datasets_data:
                dataset_id = dataset_data["dataset_id"]
                if dataset_id not in self._datasets:
                    self._datasets[dataset_id] = DatasetInfo(**dataset_data)
        except Exception as e:
            logger.warning(f"Failed to list datasets from DB: {e}")

        return list(self._datasets.values())

    async def get_dataset(self, dataset_id: str) -> DatasetInfo:
        """Get a specific dataset.

        Args:
            dataset_id: ID of dataset to retrieve

        Returns:
            DatasetInfo

        Raises:
            ValueError: If dataset not found
        """
        # Try in-memory first
        dataset = self._datasets.get(dataset_id)
        if dataset:
            return dataset

        # Fall back to DB
        try:
            await self._ensure_initialized()
            dataset_data = await self._repo.get_dataset(dataset_id)
            if dataset_data:
                dataset = DatasetInfo(**dataset_data)
                self._datasets[dataset_id] = dataset
                return dataset
        except Exception as e:
            logger.warning(f"Failed to get dataset from DB: {e}")

        raise ValueError(f"Dataset not found: {dataset_id}")


# Global instance
fine_tuning_manager = FineTuningManager()
