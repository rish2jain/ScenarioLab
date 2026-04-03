"""SQLite persistence layer for LLM-related data."""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import aiosqlite

logger = logging.getLogger(__name__)

# Database file path (same as main database)
_DB_PATH = (
    Path(__file__).resolve().parent.parent.parent / "data" / "mirofish.db"
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def get_db():
    """Get database connection (reuses the same DB file)."""
    db = await aiosqlite.connect(str(_DB_PATH))
    db.row_factory = aiosqlite.Row
    return db


async def init_llm_tables():
    """Initialize LLM-related tables."""
    db = await get_db()
    try:
        await db.executescript(
            """
            CREATE TABLE IF NOT EXISTS fine_tuning_jobs (
                job_id TEXT PRIMARY KEY,
                dataset_id TEXT,
                base_model TEXT NOT NULL,
                lora_config TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'queued',
                progress REAL DEFAULT 0.0,
                created_at TEXT NOT NULL,
                completed_at TEXT,
                metrics TEXT,
                error_message TEXT
            );

            CREATE TABLE IF NOT EXISTS fine_tuning_datasets (
                dataset_id TEXT PRIMARY KEY,
                data_type TEXT NOT NULL,
                num_examples INTEGER DEFAULT 0,
                format TEXT DEFAULT 'jsonl',
                preview_samples TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS lora_adapters (
                adapter_id TEXT PRIMARY KEY,
                job_id TEXT NOT NULL,
                base_model TEXT NOT NULL,
                domain TEXT NOT NULL,
                size_mb REAL DEFAULT 0.0,
                created_at TEXT NOT NULL,
                performance_metrics TEXT,
                active BOOLEAN DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS fine_tuning_benchmarks (
                benchmark_id TEXT PRIMARY KEY,
                domain TEXT NOT NULL,
                questions TEXT NOT NULL,
                evaluation_criteria TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS market_intelligence_configs (
                simulation_id TEXT PRIMARY KEY,
                config TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS market_intelligence_cache (
                simulation_id TEXT PRIMARY KEY,
                data TEXT NOT NULL,
                injected_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS voice_conversations (
                id TEXT PRIMARY KEY,
                simulation_id TEXT NOT NULL,
                agent_id TEXT NOT NULL,
                messages TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS voice_audio_cache (
                audio_id TEXT PRIMARY KEY,
                simulation_id TEXT NOT NULL,
                agent_id TEXT NOT NULL,
                audio_data BLOB NOT NULL,
                created_at TEXT NOT NULL
            );
            """
        )
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
        try:
            db = await get_db()
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
                    json.dumps(job.get("metrics", {}))
                    if job.get("metrics") else None,
                    job.get("error_message"),
                ),
            )
            await db.commit()
            await db.close()
        except Exception as e:
            logger.error(f"Failed to save job: {e}")

    async def get_job(self, job_id: str) -> dict | None:
        """Retrieve a fine-tuning job by ID."""
        try:
            db = await get_db()
            cursor = await db.execute(
                "SELECT * FROM fine_tuning_jobs WHERE job_id = ?",
                (job_id,),
            )
            row = await cursor.fetchone()
            await db.close()
            if row is None:
                return None
            return {
                "job_id": row["job_id"],
                "dataset_id": row["dataset_id"],
                "base_model": row["base_model"],
                "lora_config": json.loads(row["lora_config"])
                if row["lora_config"] else {},
                "status": row["status"],
                "progress": row["progress"],
                "created_at": row["created_at"],
                "completed_at": row["completed_at"],
                "metrics": json.loads(row["metrics"])
                if row["metrics"] else {},
                "error_message": row["error_message"],
            }
        except Exception as e:
            logger.error(f"Failed to get job: {e}")
            return None

    async def list_jobs(self) -> list[dict]:
        """List all fine-tuning jobs."""
        try:
            db = await get_db()
            cursor = await db.execute(
                "SELECT * FROM fine_tuning_jobs ORDER BY created_at DESC"
            )
            rows = await cursor.fetchall()
            await db.close()
            return [
                {
                    "job_id": row["job_id"],
                    "dataset_id": row["dataset_id"],
                    "base_model": row["base_model"],
                    "lora_config": json.loads(row["lora_config"])
                    if row["lora_config"] else {},
                    "status": row["status"],
                    "progress": row["progress"],
                    "created_at": row["created_at"],
                    "completed_at": row["completed_at"],
                    "metrics": json.loads(row["metrics"])
                    if row["metrics"] else {},
                    "error_message": row["error_message"],
                }
                for row in rows
            ]
        except Exception as e:
            logger.error(f"Failed to list jobs: {e}")
            return []

    async def save_dataset(self, dataset: dict) -> None:
        """Save a dataset to the database."""
        try:
            db = await get_db()
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
            await db.close()
        except Exception as e:
            logger.error(f"Failed to save dataset: {e}")

    async def get_dataset(self, dataset_id: str) -> dict | None:
        """Retrieve a dataset by ID."""
        try:
            db = await get_db()
            cursor = await db.execute(
                "SELECT * FROM fine_tuning_datasets WHERE dataset_id = ?",
                (dataset_id,),
            )
            row = await cursor.fetchone()
            await db.close()
            if row is None:
                return None
            return {
                "dataset_id": row["dataset_id"],
                "data_type": row["data_type"],
                "num_examples": row["num_examples"],
                "format": row["format"],
                "preview_samples": json.loads(row["preview_samples"])
                if row["preview_samples"] else [],
                "created_at": row["created_at"],
            }
        except Exception as e:
            logger.error(f"Failed to get dataset: {e}")
            return None

    async def list_datasets(self) -> list[dict]:
        """List all datasets."""
        try:
            db = await get_db()
            cursor = await db.execute(
                "SELECT * FROM fine_tuning_datasets ORDER BY created_at DESC"
            )
            rows = await cursor.fetchall()
            await db.close()
            return [
                {
                    "dataset_id": row["dataset_id"],
                    "data_type": row["data_type"],
                    "num_examples": row["num_examples"],
                    "format": row["format"],
                    "preview_samples": json.loads(row["preview_samples"])
                    if row["preview_samples"] else [],
                    "created_at": row["created_at"],
                }
                for row in rows
            ]
        except Exception as e:
            logger.error(f"Failed to list datasets: {e}")
            return []

    async def save_adapter(self, adapter: dict) -> None:
        """Save a LoRA adapter to the database."""
        try:
            db = await get_db()
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
            await db.close()
        except Exception as e:
            logger.error(f"Failed to save adapter: {e}")

    async def get_adapter(self, adapter_id: str) -> dict | None:
        """Retrieve an adapter by ID."""
        try:
            db = await get_db()
            cursor = await db.execute(
                "SELECT * FROM lora_adapters WHERE adapter_id = ?",
                (adapter_id,),
            )
            row = await cursor.fetchone()
            await db.close()
            if row is None:
                return None
            return {
                "adapter_id": row["adapter_id"],
                "job_id": row["job_id"],
                "base_model": row["base_model"],
                "domain": row["domain"],
                "size_mb": row["size_mb"],
                "created_at": row["created_at"],
                "performance_metrics": json.loads(row["performance_metrics"])
                if row["performance_metrics"] else {},
                "active": bool(row["active"]),
            }
        except Exception as e:
            logger.error(f"Failed to get adapter: {e}")
            return None

    async def list_adapters(self) -> list[dict]:
        """List all adapters."""
        try:
            db = await get_db()
            cursor = await db.execute(
                "SELECT * FROM lora_adapters ORDER BY created_at DESC"
            )
            rows = await cursor.fetchall()
            await db.close()
            return [
                {
                    "adapter_id": row["adapter_id"],
                    "job_id": row["job_id"],
                    "base_model": row["base_model"],
                    "domain": row["domain"],
                    "size_mb": row["size_mb"],
                    "created_at": row["created_at"],
                    "performance_metrics": json.loads(
                        row["performance_metrics"]
                    ) if row["performance_metrics"] else {},
                    "active": bool(row["active"]),
                }
                for row in rows
            ]
        except Exception as e:
            logger.error(f"Failed to list adapters: {e}")
            return []

    async def set_active_adapter(self, adapter_id: str | None) -> None:
        """Set the active adapter (deactivate all others)."""
        try:
            db = await get_db()
            # Deactivate all
            await db.execute("UPDATE lora_adapters SET active = 0")
            # Activate the specified one
            if adapter_id:
                await db.execute(
                    "UPDATE lora_adapters SET active = 1 WHERE adapter_id = ?",
                    (adapter_id,),
                )
            await db.commit()
            await db.close()
        except Exception as e:
            logger.error(f"Failed to set active adapter: {e}")

    async def get_active_adapter(self) -> dict | None:
        """Get the currently active adapter."""
        try:
            db = await get_db()
            cursor = await db.execute(
                "SELECT * FROM lora_adapters WHERE active = 1 LIMIT 1"
            )
            row = await cursor.fetchone()
            await db.close()
            if row is None:
                return None
            return {
                "adapter_id": row["adapter_id"],
                "job_id": row["job_id"],
                "base_model": row["base_model"],
                "domain": row["domain"],
                "size_mb": row["size_mb"],
                "created_at": row["created_at"],
                "performance_metrics": json.loads(row["performance_metrics"])
                if row["performance_metrics"] else {},
                "active": bool(row["active"]),
            }
        except Exception as e:
            logger.error(f"Failed to get active adapter: {e}")
            return None

    async def save_benchmark(self, benchmark: dict) -> None:
        """Save a benchmark to the database."""
        try:
            db = await get_db()
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
            await db.close()
        except Exception as e:
            logger.error(f"Failed to save benchmark: {e}")

    async def get_benchmark(self, benchmark_id: str) -> dict | None:
        """Retrieve a benchmark by ID."""
        try:
            db = await get_db()
            cursor = await db.execute(
                "SELECT * FROM fine_tuning_benchmarks WHERE benchmark_id = ?",
                (benchmark_id,),
            )
            row = await cursor.fetchone()
            await db.close()
            if row is None:
                return None
            return {
                "benchmark_id": row["benchmark_id"],
                "domain": row["domain"],
                "questions": json.loads(row["questions"])
                if row["questions"] else [],
                "evaluation_criteria": json.loads(row["evaluation_criteria"])
                if row["evaluation_criteria"] else [],
                "created_at": row["created_at"],
            }
        except Exception as e:
            logger.error(f"Failed to get benchmark: {e}")
            return None

    async def list_benchmarks(self) -> list[dict]:
        """List all benchmarks."""
        try:
            db = await get_db()
            cursor = await db.execute(
                "SELECT * FROM fine_tuning_benchmarks ORDER BY created_at DESC"
            )
            rows = await cursor.fetchall()
            await db.close()
            return [
                {
                    "benchmark_id": row["benchmark_id"],
                    "domain": row["domain"],
                    "questions": json.loads(row["questions"])
                    if row["questions"] else [],
                    "evaluation_criteria": json.loads(
                        row["evaluation_criteria"]
                    ) if row["evaluation_criteria"] else [],
                    "created_at": row["created_at"],
                }
                for row in rows
            ]
        except Exception as e:
            logger.error(f"Failed to list benchmarks: {e}")
            return []


class MarketIntelligenceRepository:
    """CRUD operations for market intelligence persistence."""

    async def save_config(self, simulation_id: str, config: dict) -> None:
        """Save market intelligence config for a simulation."""
        try:
            db = await get_db()
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
            await db.close()
        except Exception as e:
            logger.error(f"Failed to save market config: {e}")

    async def get_config(self, simulation_id: str) -> dict | None:
        """Retrieve market intelligence config for a simulation."""
        try:
            db = await get_db()
            cursor = await db.execute(
                "SELECT config FROM market_intelligence_configs "
                "WHERE simulation_id = ?",
                (simulation_id,),
            )
            row = await cursor.fetchone()
            await db.close()
            if row is None:
                return None
            return json.loads(row["config"])
        except Exception as e:
            logger.error(f"Failed to get market config: {e}")
            return None

    async def save_cache(self, simulation_id: str, data: dict) -> None:
        """Save market intelligence cache for a simulation."""
        try:
            db = await get_db()
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
            await db.close()
        except Exception as e:
            logger.error(f"Failed to save market cache: {e}")

    async def get_cache(self, simulation_id: str) -> dict | None:
        """Retrieve market intelligence cache for a simulation."""
        try:
            db = await get_db()
            cursor = await db.execute(
                "SELECT data FROM market_intelligence_cache "
                "WHERE simulation_id = ?",
                (simulation_id,),
            )
            row = await cursor.fetchone()
            await db.close()
            if row is None:
                return None
            return json.loads(row["data"])
        except Exception as e:
            logger.error(f"Failed to get market cache: {e}")
            return None


class VoiceRepository:
    """CRUD operations for voice conversation persistence."""

    async def save_conversation(
        self, simulation_id: str, agent_id: str, messages: list[dict]
    ) -> None:
        """Save conversation history for a simulation/agent."""
        try:
            db = await get_db()
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
            await db.close()
        except Exception as e:
            logger.error(f"Failed to save conversation: {e}")

    async def get_conversation(
        self, simulation_id: str, agent_id: str
    ) -> list[dict] | None:
        """Retrieve conversation history for a simulation/agent."""
        try:
            db = await get_db()
            cursor = await db.execute(
                "SELECT messages FROM voice_conversations "
                "WHERE simulation_id = ? AND agent_id = ?",
                (simulation_id, agent_id),
            )
            row = await cursor.fetchone()
            await db.close()
            if row is None:
                return None
            return json.loads(row["messages"])
        except Exception as e:
            logger.error(f"Failed to get conversation: {e}")
            return None

    async def delete_conversation(
        self, simulation_id: str, agent_id: str | None = None
    ) -> None:
        """Delete conversation history."""
        try:
            db = await get_db()
            if agent_id:
                await db.execute(
                    "DELETE FROM voice_conversations "
                    "WHERE simulation_id = ? AND agent_id = ?",
                    (simulation_id, agent_id),
                )
            else:
                await db.execute(
                    "DELETE FROM voice_conversations WHERE simulation_id = ?",
                    (simulation_id,),
                )
            await db.commit()
            await db.close()
        except Exception as e:
            logger.error(f"Failed to delete conversation: {e}")

    async def save_audio(
        self,
        audio_id: str,
        simulation_id: str,
        agent_id: str,
        audio_data: bytes,
    ) -> None:
        """Save audio data to the database."""
        try:
            db = await get_db()
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
            await db.close()
        except Exception as e:
            logger.error(f"Failed to save audio: {e}")

    async def get_audio(self, audio_id: str) -> bytes | None:
        """Retrieve audio data by ID."""
        try:
            db = await get_db()
            cursor = await db.execute(
                "SELECT audio_data FROM voice_audio_cache WHERE audio_id = ?",
                (audio_id,),
            )
            row = await cursor.fetchone()
            await db.close()
            if row is None:
                return None
            return row["audio_data"]
        except Exception as e:
            logger.error(f"Failed to get audio: {e}")
            return None

    async def delete_audio_for_simulation(
        self, simulation_id: str, agent_id: str | None = None
    ) -> None:
        """Delete audio cache for a simulation."""
        try:
            db = await get_db()
            if agent_id:
                await db.execute(
                    "DELETE FROM voice_audio_cache "
                    "WHERE simulation_id = ? AND agent_id = ?",
                    (simulation_id, agent_id),
                )
            else:
                await db.execute(
                    "DELETE FROM voice_audio_cache WHERE simulation_id = ?",
                    (simulation_id,),
                )
            await db.commit()
            await db.close()
        except Exception as e:
            logger.error(f"Failed to delete audio: {e}")
