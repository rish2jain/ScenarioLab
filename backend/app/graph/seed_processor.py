"""Document ingestion and processing for seed materials."""

import logging
import uuid

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# In-memory cache for seed materials (backed by SQLite via SeedRepository)
_seed_store: dict[str, "SeedMaterial"] = {}


class SeedMaterial(BaseModel):
    """Represents a processed seed material document."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    filename: str
    content_type: str  # "text/plain", "text/markdown", "application/pdf"
    raw_content: str
    processed_content: str | None = None
    status: str = "uploaded"  # uploaded, processing, processed, failed
    entity_count: int = 0
    relationship_count: int = 0
    error_message: str | None = None


class SeedProcessor:
    """Processes seed materials into structured content."""

    def __init__(self):
        self._store = _seed_store
        self._repo: object | None = None

    def _get_repo(self):
        """Lazy-import SeedRepository to avoid circular imports."""
        if self._repo is None:
            from app.database import SeedRepository

            self._repo = SeedRepository()
        return self._repo

    def get_store(self) -> dict[str, SeedMaterial]:
        """Get the seed material store."""
        return self._store

    async def process_file(
        self, filename: str, content: bytes, content_type: str
    ) -> SeedMaterial:
        """Process an uploaded file into a SeedMaterial."""
        seed = SeedMaterial(
            filename=filename,
            content_type=content_type,
            raw_content="",
        )

        try:
            seed.status = "processing"

            # Extract text based on content type
            if content_type == "application/pdf":
                raw_text = await self.extract_text_from_pdf(content)
            elif content_type in ("text/plain", "text/markdown", "text/text"):
                raw_text = content.decode("utf-8", errors="ignore")
            else:
                # Try to decode as text for unknown types
                try:
                    raw_text = content.decode("utf-8", errors="ignore")
                except Exception:
                    raise ValueError(
                        f"Unsupported content type: {content_type}"
                    )

            seed.raw_content = raw_text
            # Can add additional processing later
            seed.processed_content = raw_text
            seed.status = "processed"

            logger.info(
                f"Processed {filename} ({content_type}) -> "
                f"{len(raw_text)} chars"
            )

        except Exception as e:
            seed.status = "failed"
            seed.error_message = str(e)
            logger.error(f"Failed to process file {filename}: {e}")

        # Store in memory and persist to DB
        self._store[seed.id] = seed
        await self._get_repo().save(seed)
        return seed

    async def extract_text_from_pdf(self, content: bytes) -> str:
        """Extract text from PDF bytes.

        Uses a simple best-effort approach. For production use,
        consider adding pdfplumber or PyPDF2 dependency.
        """
        try:
            # Try to extract text using basic PDF text extraction
            # PDF files have text embedded between streams
            text_parts = []

            # Simple heuristic: look for text between BT (Begin Text)
            # and ET (End Text)
            # and between stream/endstream
            import re

            # Try to decode as utf-8 first, ignoring errors
            decoded = content.decode("utf-8", errors="ignore")

            # Look for text in parentheses (common PDF text format)
            text_in_parens = re.findall(r'\(([^)]+)\)', decoded)

            # Filter out short strings and binary-looking content
            for text in text_in_parens:
                if len(text) > 3 and all(ord(c) < 128 for c in text):
                    text_parts.append(text)

            if text_parts:
                return " ".join(text_parts)

            # Fallback: try to extract readable ASCII text
            readable_chars = []
            for byte in content:
                # printable ASCII or newline
                if 32 <= byte <= 126 or byte in (10, 13):
                    readable_chars.append(chr(byte))

            extracted = "".join(readable_chars)

            # Clean up: remove excessive whitespace
            lines = [
                line.strip() for line in extracted.split('\n') if line.strip()
            ]
            cleaned_text = "\n".join(lines)

            if len(cleaned_text) > 100:
                return cleaned_text

            # If extraction yields very little, return a placeholder
            logger.warning(
                "PDF text extraction yielded limited results. "
                "Consider adding pdfplumber."
            )
            return (
                f"[PDF: {len(content)} bytes. Basic extraction applied.]\n\n"
                f"{cleaned_text[:2000]}"
            )

        except Exception as e:
            logger.error(f"PDF extraction error: {e}")
            return f"[PDF extraction failed: {str(e)}]"

    async def chunk_content(
        self, content: str, chunk_size: int = 2000, overlap: int = 200
    ) -> list[str]:
        """Split content into overlapping chunks for processing."""
        if not content:
            return []

        chunks = []
        start = 0
        content_length = len(content)

        while start < content_length:
            end = min(start + chunk_size, content_length)

            # Try to break at a sentence or word boundary
            if end < content_length:
                # Look for sentence endings
                for i in range(min(end + 100, content_length) - 1, start, -1):
                    if content[i] in '.!?':
                        end = i + 1
                        break
                else:
                    # Look for word boundaries
                    for i in range(end, start, -1):
                        if content[i - 1].isspace():
                            end = i
                            break

            chunk = content[start:end].strip()
            if chunk:
                chunks.append(chunk)

            # Move start forward with overlap
            start = end - overlap if end < content_length else content_length

        logger.info(
            f"Chunked into {len(chunks)} chunks "
            f"(size={chunk_size}, overlap={overlap})"
        )
        return chunks

    async def get_seed(self, seed_id: str) -> SeedMaterial | None:
        """Get a seed material by ID (in-memory first, then DB)."""
        cached = self._store.get(seed_id)
        if cached is not None:
            return cached
        seed = await self._get_repo().get(seed_id)
        if seed is not None:
            self._store[seed_id] = seed
        return seed

    async def list_seeds(self) -> list[SeedMaterial]:
        """List all seed materials from DB."""
        db_summaries = await self._get_repo().list_all()
        seeds: list[SeedMaterial] = []
        for summary in db_summaries:
            seed_id = summary["id"]
            cached = self._store.get(seed_id)
            if cached is not None:
                seeds.append(cached)
            else:
                seed = await self._get_repo().get(seed_id)
                if seed is not None:
                    self._store[seed_id] = seed
                    seeds.append(seed)
        return seeds

    async def update_seed(self, seed_id: str, **updates) -> SeedMaterial | None:
        """Update a seed material in memory and DB."""
        seed = await self.get_seed(seed_id)
        if seed is None:
            return None

        for key, value in updates.items():
            if hasattr(seed, key):
                setattr(seed, key, value)

        self._store[seed_id] = seed
        await self._get_repo().save(seed)
        return seed
