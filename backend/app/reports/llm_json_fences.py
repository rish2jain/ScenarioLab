"""Strip markdown ``` / ```json fences from LLM output before JSON parsing."""

import re

_JSON_FENCE_RE = re.compile(r"^\s*```(?:json)?\s*\n?", re.IGNORECASE)
_FENCE_END_RE = re.compile(r"\n?```\s*$")


def strip_llm_json_fences(raw: str) -> str:
    """Remove optional opening/closing code fences (whitespace/case tolerant)."""
    s = raw.strip()
    s = _JSON_FENCE_RE.sub("", s)
    s = _FENCE_END_RE.sub("", s)
    return s.strip()
