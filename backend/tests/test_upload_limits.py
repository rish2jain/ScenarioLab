"""Tests for capped upload reads."""

from io import BytesIO
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException, UploadFile

from app.upload_limits import read_upload_limited


def _upload(data: bytes) -> UploadFile:
    return UploadFile(filename="t.bin", file=BytesIO(data))


@pytest.mark.asyncio
async def test_read_upload_limited_returns_bytes():
    data = b"hello-world"
    out = await read_upload_limited(_upload(data), max_bytes=100)
    assert out == data


@pytest.mark.asyncio
async def test_read_upload_limited_rejects_oversize():
    data = b"x" * 50
    with pytest.raises(HTTPException) as exc:
        await read_upload_limited(_upload(data), max_bytes=40)
    assert exc.value.status_code == 413


@pytest.mark.asyncio
async def test_read_upload_limited_stops_after_cap():
    """Ensure we do not keep reading after the cap is hit."""
    file = UploadFile(filename="big.bin", file=BytesIO(b"a" * 200))
    file.read = AsyncMock(side_effect=[b"a" * 30, b"a" * 30, b""])
    with pytest.raises(HTTPException) as exc:
        await read_upload_limited(file, max_bytes=50)
    assert exc.value.status_code == 413
    assert file.read.await_count == 2
