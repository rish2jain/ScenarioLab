"""SQLite persistence layer for LLM-related data.

Connection management and DDL are delegated to ``app.db.connection``.
"""

import json
import logging
from typing import Any

from app.db.connection import LLM_DDL, get_fresh_db
from app.db.connection import utc_now_iso as _utc_now_iso

logger = logging.getLogger(__name__)


def _json_or(value: str | None, default: Any) -> Any:
    """Parse a JSON column or return ``default`` when empty/None."""
    if not value:
        return default
    return json.loads(value)


def _row_to_job(row: Any) -> dict[str, Any]:
    # ``num_examples`` is not a column on ``fine_tuning_jobs`` (see LLM_DDL);
    # ``FineTuningJob.num_examples`` is filled lazily via
    # ``fine_tuning.FineTuningService._with_dataset_examples`` after loading.
    return {
        "job_id": row["job_id"],
        "dataset_id": row["dataset_id"],
        "base_model": row["base_model"],
        "lora_config": _json_or(row["lora_config"], {}),
        "status": row["status"],
        "progress": row["progress"],
        "created_at": row["created_at"],
        "completed_at": row["completed_at"],
        "metrics": _json_or(row["metrics"], {}),
        "error_message": row["error_message"],
    }


def _row_to_dataset(row: Any) -> dict[str, Any]:
    return {
        "dataset_id": row["dataset_id"],
        "data_type": row["data_type"],
        "num_examples": row["num_examples"],
        "format": row["format"],
        "preview_samples": _json_or(row["preview_samples"], []),
        "created_at": row["created_at"],
    }


def _row_to_adapter(row: Any) -> dict[str, Any]:
    return {
        "adapter_id": row["adapter_id"],
        "job_id": row["job_id"],
        "base_model": row["base_model"],
        "domain": row["domain"],
        "size_mb": row["size_mb"],
        "created_at": row["created_at"],
        "performance_metrics": _json_or(row["performance_metrics"], {}),
        "active": bool(row["active"]),
    }


def _row_to_benchmark(row: Any) -> dict[str, Any]:
    return {
        "benchmark_id": row["benchmark_id"],
        "domain": row["domain"],
        "questions": _json_or(row["questions"], []),
        "evaluation_criteria": _json_or(row["evaluation_criteria"], []),
        "created_at": row["created_at"],
    }


async def get_db():
    """Get database connection (reuses the same DB file)."""
    return await get_fresh_db()


async def init_llm_tables() -> None:
    """Initialize LLM-related tables."""
    db = await get_db()
    try:
        await db.executescript(LLM_DDL)
        await db.commit()
        logger.info("LLM tables initialized")
    except Exception as e:
        logger.error(f"Failed to initialize LLM tables: {e}")
        raise
    finally:
        await db.close()


class FineTuningRepository:
    """CRUD operations for fine-tuning persistence."""

    async def save_job(self, job: dict) -> None:
        """Save a fine-tuning job to the database."""
        db = await get_db()
        try:
            await db.execute(
                """
                INSERT INTO fine_tuning_jobs
                    (job_id, dataset_id, base_model, lora_config,
                     status, progress, created_at, completed_at,
                     metrics, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(job_id) DO UPDATE SET
                    dataset_id = excluded.dataset_id,
                    base_model = excluded.base_model,
                    lora_config = excluded.lora_config,
                    status = excluded.status,
                    progress = excluded.progress,
                    completed_at = excluded.completed_at,
                    metrics = excluded.metrics,
                    error_message = excluded.error_message
                """,
                (
                    job["job_id"],
                    job.get("dataset_id"),
                    job["base_model"],
                    json.dumps(job.get("lora_config", {})),
                    job.get("status", "queued"),
                    job.get("progress", 0.0),
                    job.get("created_at", _utc_now_iso()),
                    job.get("completed_at"),
                    json.dumps(job.get("metrics", {})),
                    job.get("error_message"),
                ),
            )
            await db.commit()
        except Exception as e:
            logger.error(f"Failed to save job: {e}")
            raise
        finally:
            await db.close()

    async def get_job(self, job_id: str) -> dict | None:
        """Retrieve a fine-tuning job by ID."""
        db = await get_db()
        try:
            cursor = await db.execute(
                "SELECT * FROM fine_tuning_jobs WHERE job_id = ?",
                (job_id,),
            )
            row = await cursor.fetchone()
            if row is None:
                return None
            return _row_to_job(row)
        except Exception as e:
            logger.error(f"Failed to get job: {e}")
            return None
        finally:
            await db.close()

    async def list_jobs(self) -> list[dict]:
        """List all fine-tuning jobs."""
        db = await get_db()
        try:
            cursor = await db.execute("SELECT * FROM fine_tuning_jobs ORDER BY created_at DESC")
            rows = await cursor.fetchall()
            return [_row_to_job(r) for r in rows]
        except Exception as e:
            logger.error(f"Failed to list jobs: {e}")
            return []
        finally:
            await db.close()

    async def save_dataset(self, dataset: dict) -> None:
        """Save a dataset to the database."""
        db = await get_db()
        try:
            await db.execute(
                """
                INSERT INTO fine_tuning_datasets
                    (dataset_id, data_type, num_examples, format,
                     preview_samples, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(dataset_id) DO UPDATE SET
                    data_type = excluded.data_type,
                    num_examples = excluded.num_examples,
                    format = excluded.format,
                    preview_samples = excluded.preview_samples
                """,
                (
                    dataset["dataset_id"],
                    dataset["data_type"],
                    dataset.get("num_examples", 0),
                    dataset.get("format", "jsonl"),
                    json.dumps(dataset.get("preview_samples", [])),
                    dataset.get("created_at", _utc_now_iso()),
                ),
            )
            await db.commit()
        except Exception as e:
            logger.error(f"Failed to save dataset: {e}")
            raise
        finally:
            await db.close()

    async def get_dataset(self, dataset_id: str) -> dict | None:
        """Retrieve a dataset by ID."""
        db = await get_db()
        try:
            cursor = await db.execute(
                "SELECT * FROM fine_tuning_datasets WHERE dataset_id = ?",
                (dataset_id,),
            )
            row = await cursor.fetchone()
            if row is None:
                return None
            return _row_to_dataset(row)
        except Exception as e:
            logger.error(f"Failed to get dataset: {e}")
            return None
        finally:
            await db.close()

    async def list_datasets(self) -> list[dict]:
        """List all datasets."""
        db = await get_db()
        try:
            cursor = await db.execute("SELECT * FROM fine_tuning_datasets ORDER BY created_at DESC")
            rows = await cursor.fetchall()
            return [_row_to_dataset(r) for r in rows]
        except Exception as e:
            logger.error(f"Failed to list datasets: {e}")
            return []
        finally:
            await db.close()

    async def save_adapter(self, adapter: dict) -> None:
        """Save a LoRA adapter to the database."""
        db = await get_db()
        try:
            await db.execute(
                """
                INSERT INTO lora_adapters
                    (adapter_id, job_id, base_model, domain, size_mb,
                     created_at, performance_metrics, active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(adapter_id) DO UPDATE SET
                    job_id = excluded.job_id,
                    base_model = excluded.base_model,
                    domain = excluded.domain,
                    size_mb = excluded.size_mb,
                    performance_metrics = excluded.performance_metrics,
                    active = excluded.active
                """,
                (
                    adapter["adapter_id"],
                    adapter["job_id"],
                    adapter["base_model"],
                    adapter["domain"],
                    adapter.get("size_mb", 0.0),
                    adapter.get("created_at", _utc_now_iso()),
                    json.dumps(adapter.get("performance_metrics", {})),
                    1 if adapter.get("active", False) else 0,
                ),
            )
            await db.commit()
        except Exception as e:
            logger.error(f"Failed to save adapter: {e}")
            raise
        finally:
            await db.close()

    async def get_adapter(self, adapter_id: str) -> dict | None:
        """Retrieve an adapter by ID."""
        db = await get_db()
        try:
            cursor = await db.execute(
                "SELECT * FROM lora_adapters WHERE adapter_id = ?",
                (adapter_id,),
            )
            row = await cursor.fetchone()
            if row is None:
                return None
            return _row_to_adapter(row)
        except Exception as e:
            logger.error(f"Failed to get adapter: {e}")
            return None
        finally:
            await db.close()

    async def list_adapters(self) -> list[dict]:
        """List all adapters."""
        db = await get_db()
        try:
            cursor = await db.execute("SELECT * FROM lora_adapters ORDER BY created_at DESC")
            rows = await cursor.fetchall()
            return [_row_to_adapter(r) for r in rows]
        except Exception as e:
            logger.error(f"Failed to list adapters: {e}")
            return []
        finally:
            await db.close()

    async def set_active_adapter(self, adapter_id: str | None) -> None:
        """Set the active adapter (deactivate all others)."""
        db = await get_db()
        try:
            # Deactivate all
            await db.execute("UPDATE lora_adapters SET active = 0")
            # Activate the specified one
            if adapter_id:
                await db.execute(
                    "UPDATE lora_adapters SET active = 1 WHERE adapter_id = ?",
                    (adapter_id,),
                )
            await db.commit()
        except Exception as e:
            logger.error(f"Failed to set active adapter: {e}")
            raise
        finally:
            await db.close()

    async def get_active_adapter(self) -> dict | None:
        """Get the currently active adapter."""
        db = await get_db()
        try:
            cursor = await db.execute("SELECT * FROM lora_adapters WHERE active = 1 LIMIT 1")
            row = await cursor.fetchone()
            if row is None:
                return None
            return _row_to_adapter(row)
        except Exception as e:
            logger.error(f"Failed to get active adapter: {e}")
            return None
        finally:
            await db.close()

    async def save_benchmark(self, benchmark: dict) -> None:
        """Save a benchmark to the database."""
        db = await get_db()
        try:
            await db.execute(
                """
                INSERT INTO fine_tuning_benchmarks
                    (benchmark_id, domain, questions,
                     evaluation_criteria, created_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(benchmark_id) DO UPDATE SET
                    domain = excluded.domain,
                    questions = excluded.questions,
                    evaluation_criteria = excluded.evaluation_criteria
                """,
                (
                    benchmark["benchmark_id"],
                    benchmark["domain"],
                    json.dumps(benchmark.get("questions", [])),
                    json.dumps(benchmark.get("evaluation_criteria", [])),
                    benchmark.get("created_at", _utc_now_iso()),
                ),
            )
            await db.commit()
        except Exception as e:
            logger.error(f"Failed to save benchmark: {e}")
            raise
        finally:
            await db.close()

    async def get_benchmark(self, benchmark_id: str) -> dict | None:
        """Retrieve a benchmark by ID."""
        db = await get_db()
        try:
            cursor = await db.execute(
                "SELECT * FROM fine_tuning_benchmarks WHERE benchmark_id = ?",
                (benchmark_id,),
            )
            row = await cursor.fetchone()
            if row is None:
                return None
            return _row_to_benchmark(row)
        except Exception as e:
            logger.error(f"Failed to get benchmark: {e}")
            return None
        finally:
            await db.close()

    async def list_benchmarks(self) -> list[dict]:
        """List all benchmarks."""
        db = await get_db()
        try:
            cursor = await db.execute("SELECT * FROM fine_tuning_benchmarks ORDER BY created_at DESC")
            rows = await cursor.fetchall()
            return [_row_to_benchmark(r) for r in rows]
        except Exception as e:
            logger.error(f"Failed to list benchmarks: {e}")
            return []
        finally:
            await db.close()


class MarketIntelligenceRepository:
    """CRUD operations for market intelligence persistence."""

    async def save_config(self, simulation_id: str, config: dict) -> None:
        """Save market intelligence config for a simulation."""
        db = await get_db()
        try:
            await db.execute(
                """
                INSERT INTO market_intelligence_configs
                    (simulation_id, config, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(simulation_id) DO UPDATE SET
                    config = excluded.config,
                    updated_at = excluded.updated_at
                """,
                (simulation_id, json.dumps(config), _utc_now_iso()),
            )
            await db.commit()
        except Exception as e:
            logger.error(f"Failed to save market config: {e}")
            raise
        finally:
            await db.close()

    async def get_config(self, simulation_id: str) -> dict | None:
        """Retrieve market intelligence config for a simulation."""
        db = await get_db()
        try:
            cursor = await db.execute(
                "SELECT config FROM market_intelligence_configs " "WHERE simulation_id = ?",
                (simulation_id,),
            )
            row = await cursor.fetchone()
            if row is None:
                return None
            return json.loads(row["config"])
        except Exception as e:
            logger.error(f"Failed to get market config: {e}")
            return None
        finally:
            await db.close()

    async def save_cache(self, simulation_id: str, data: dict) -> None:
        """Save market intelligence cache for a simulation."""
        db = await get_db()
        try:
            await db.execute(
                """
                INSERT INTO market_intelligence_cache
                    (simulation_id, data, injected_at)
                VALUES (?, ?, ?)
                ON CONFLICT(simulation_id) DO UPDATE SET
                    data = excluded.data,
                    injected_at = excluded.injected_at
                """,
                (simulation_id, json.dumps(data), _utc_now_iso()),
            )
            await db.commit()
        except Exception as e:
            logger.error(f"Failed to save market cache: {e}")
            raise
        finally:
            await db.close()

    async def get_cache(self, simulation_id: str) -> dict | None:
        """Retrieve market intelligence cache for a simulation."""
        db = await get_db()
        try:
            cursor = await db.execute(
                "SELECT data FROM market_intelligence_cache " "WHERE simulation_id = ?",
                (simulation_id,),
            )
            row = await cursor.fetchone()
            if row is None:
                return None
            return json.loads(row["data"])
        except Exception as e:
            logger.error(f"Failed to get market cache: {e}")
            return None
        finally:
            await db.close()


class VoiceRepository:
    """CRUD operations for voice conversation persistence."""

    async def save_conversation(self, simulation_id: str, agent_id: str, messages: list[dict]) -> None:
        """Save conversation history for a simulation/agent."""
        db = await get_db()
        try:
            conversation_id = f"{simulation_id}:{agent_id}"
            await db.execute(
                """
                INSERT INTO voice_conversations
                    (id, simulation_id, agent_id, messages, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    messages = excluded.messages,
                    updated_at = excluded.updated_at
                """,
                (
                    conversation_id,
                    simulation_id,
                    agent_id,
                    json.dumps(messages),
                    _utc_now_iso(),
                ),
            )
            await db.commit()
        except Exception as e:
            logger.error(f"Failed to save conversation: {e}")
            raise
        finally:
            await db.close()

    async def get_conversation(self, simulation_id: str, agent_id: str) -> list[dict] | None:
        """Retrieve conversation history for a simulation/agent."""
        db = await get_db()
        try:
            cursor = await db.execute(
                "SELECT messages FROM voice_conversations " "WHERE simulation_id = ? AND agent_id = ?",
                (simulation_id, agent_id),
            )
            row = await cursor.fetchone()
            if row is None:
                return None
            return json.loads(row["messages"])
        except Exception as e:
            logger.error(f"Failed to get conversation: {e}")
            return None
        finally:
            await db.close()

    async def delete_conversation(self, simulation_id: str, agent_id: str | None = None) -> None:
        """Delete conversation history."""
        db = await get_db()
        try:
            if agent_id:
                await db.execute(
                    "DELETE FROM voice_conversations " "WHERE simulation_id = ? AND agent_id = ?",
                    (simulation_id, agent_id),
                )
            else:
                await db.execute(
                    "DELETE FROM voice_conversations WHERE simulation_id = ?",
                    (simulation_id,),
                )
            await db.commit()
        except Exception as e:
            logger.error(f"Failed to delete conversation: {e}")
            raise
        finally:
            await db.close()

    async def save_audio(
        self,
        audio_id: str,
        simulation_id: str,
        agent_id: str,
        audio_data: bytes,
    ) -> None:
        """Save audio data to the database."""
        db = await get_db()
        try:
            await db.execute(
                """
                INSERT INTO voice_audio_cache
                    (audio_id, simulation_id, agent_id, audio_data, created_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(audio_id) DO UPDATE SET
                    audio_data = excluded.audio_data,
                    created_at = excluded.created_at
                """,
                (
                    audio_id,
                    simulation_id,
                    agent_id,
                    audio_data,
                    _utc_now_iso(),
                ),
            )
            await db.commit()
        except Exception as e:
            logger.error(f"Failed to save audio: {e}")
            raise
        finally:
            await db.close()

    async def get_audio(self, audio_id: str) -> bytes | None:
        """Retrieve audio data by ID."""
        db = await get_db()
        try:
            cursor = await db.execute(
                "SELECT audio_data FROM voice_audio_cache WHERE audio_id = ?",
                (audio_id,),
            )
            row = await cursor.fetchone()
            if row is None:
                return None
            return row["audio_data"]
        except Exception as e:
            logger.error(f"Failed to get audio: {e}")
            return None
        finally:
            await db.close()

    async def delete_audio_for_simulation(self, simulation_id: str, agent_id: str | None = None) -> None:
        """Delete audio cache for a simulation."""
        db = await get_db()
        try:
            if agent_id:
                await db.execute(
                    "DELETE FROM voice_audio_cache " "WHERE simulation_id = ? AND agent_id = ?",
                    (simulation_id, agent_id),
                )
            else:
                await db.execute(
                    "DELETE FROM voice_audio_cache WHERE simulation_id = ?",
                    (simulation_id,),
                )
            await db.commit()
        except Exception as e:
            logger.error(f"Failed to delete audio: {e}")
            raise
        finally:
            await db.close()
