"""Helpers for reading uploads with a hard byte cap."""

from fastapi import HTTPException, UploadFile


async def read_upload_limited(file: UploadFile, max_bytes: int) -> bytes:
    """Read an upload up to ``max_bytes``; raise HTTP 413 if exceeded."""
    if max_bytes <= 0:
        raise HTTPException(status_code=500, detail="Upload size limit is misconfigured")

    chunks: list[bytes] = []
    total = 0
    # Read in chunks so oversized uploads never fully buffer in memory.
    chunk_size = min(64 * 1024, max_bytes)
    while True:
        chunk = await file.read(chunk_size)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"Upload exceeds maximum size of {max_bytes} bytes",
            )
        chunks.append(chunk)
    return b"".join(chunks)
