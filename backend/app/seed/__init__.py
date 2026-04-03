"""Seed material processing package."""

from app.seed.multilanguage import (
    SUPPORTED_LANGUAGES,
    LanguageDetectionResult,
    MultiLanguageProcessor,
)

__all__ = [
    "MultiLanguageProcessor",
    "LanguageDetectionResult",
    "SUPPORTED_LANGUAGES",
]
