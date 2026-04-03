"""Multi-language support for seed material processing."""

import logging

from pydantic import BaseModel, Field

from app.llm.provider import LLMMessage, LLMProvider

logger = logging.getLogger(__name__)

SUPPORTED_LANGUAGES = ["en", "de", "fr", "es", "ja", "zh", "ko", "pt", "ar"]


class LanguageDetectionResult(BaseModel):
    """Result of language detection."""

    detected_language: str
    confidence: float = Field(..., ge=0.0, le=1.0)


class MultiLanguageProcessor:
    """Processes seed material in multiple languages."""

    def __init__(self, llm_provider: LLMProvider | None = None):
        self.llm = llm_provider

    async def detect_language(self, text: str) -> LanguageDetectionResult:
        """Detect language of text using LLM.

        Args:
            text: Text to analyze

        Returns:
            LanguageDetectionResult with detected language code
        """
        if not self.llm:
            # Simple heuristic fallback
            return self._heuristic_language_detection(text)

        prompt = f"""Detect the language of the following text.

TEXT (first 500 chars):
{text[:500]}

Respond with a JSON object:
{{
    "language_code": "en|de|fr|es|ja|zh|ko|pt|ar",
    "confidence": 0.0-1.0
}}

Use ISO 639-1 language codes. Respond with valid JSON only."""

        try:
            response = await self.llm.generate(
                messages=[
                    LLMMessage(
                        role="system",
                        content="You detect the language of text. "
                                "Respond with valid JSON only.",
                    ),
                    LLMMessage(role="user", content=prompt),
                ],
                temperature=0.1,
                max_tokens=100,
            )

            import json

            content = response.content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

            data = json.loads(content)
            detected = data.get("language_code", "en")

            # Validate against supported languages
            if detected not in SUPPORTED_LANGUAGES:
                detected = "en"

            return LanguageDetectionResult(
                detected_language=detected,
                confidence=data.get("confidence", 0.8),
            )

        except Exception as e:
            logger.error(f"Failed to detect language with LLM: {e}")
            return self._heuristic_language_detection(text)

    def _heuristic_language_detection(self, text: str) -> LanguageDetectionResult:
        """Simple heuristic language detection."""
        text_lower = text.lower()

        # Simple character-based detection
        if any(ord(c) > 127 for c in text[:100]):
            # Check for specific scripts
            for char in text[:100]:
                code = ord(char)
                # Japanese Hiragana/Katakana
                if 0x3040 <= code <= 0x309F or 0x30A0 <= code <= 0x30FF:
                    return LanguageDetectionResult(
                        detected_language="ja", confidence=0.7
                    )
                # Chinese
                if 0x4E00 <= code <= 0x9FFF:
                    return LanguageDetectionResult(
                        detected_language="zh", confidence=0.7
                    )
                # Korean
                if 0xAC00 <= code <= 0xD7AF:
                    return LanguageDetectionResult(
                        detected_language="ko", confidence=0.7
                    )
                # Arabic
                if 0x0600 <= code <= 0x06FF:
                    return LanguageDetectionResult(
                        detected_language="ar", confidence=0.7
                    )

        # Default to English
        return LanguageDetectionResult(detected_language="en", confidence=0.9)

    async def translate_to_english(
        self, text: str, source_language: str
    ) -> str:
        """Translate text to English for processing, preserving key terms.

        Args:
            text: Text to translate
            source_language: Source language code

        Returns:
            Translated text
        """
        if source_language == "en":
            return text

        if not self.llm:
            logger.warning("LLM not available for translation, returning original")
            return text

        prompt = f"""Translate the following text from {source_language} to English.

IMPORTANT:
- Preserve company names, product names, and proper nouns in original form
- Keep industry-specific terminology that may not translate well
- Maintain the formal/business tone of the original

TEXT:
{text[:2000]}

Provide only the translated text, no explanations."""

        try:
            response = await self.llm.generate(
                messages=[
                    LLMMessage(
                        role="system",
                        content=(
                            "You are a professional translator specializing "
                            "in business and strategic documents. "
                            "Preserve key terms and names."
                        ),
                    ),
                    LLMMessage(role="user", content=prompt),
                ],
                temperature=0.3,
                max_tokens=2000,
            )

            return response.content.strip()

        except Exception as e:
            logger.error(f"Failed to translate text: {e}")
            return text

    async def process_multilanguage_seed(self, content: str) -> dict:
        """Process seed material in any supported language.

        Args:
            content: Seed material content

        Returns:
            Dictionary with processed content and metadata
        """
        # Detect language
        detection = await self.detect_language(content)

        # Translate if needed
        translated_content = content
        if detection.detected_language != "en":
            translated_content = await self.translate_to_english(
                content, detection.detected_language
            )

        return {
            "original_content": content,
            "translated_content": translated_content,
            "detected_language": detection.detected_language,
            "detection_confidence": detection.confidence,
            "was_translated": detection.detected_language != "en",
        }
