"""Analytics module — named constants for keyword lists, regex patterns,
and other heuristic definitions used by AnalyticsAgent.

Separating these from the class keeps analytics_agent.py focused on
algorithm logic and makes the heuristics easy to tune without touching
method signatures or control flow.
"""

# ---------------------------------------------------------------------------
# Sentiment keyword lists
# ---------------------------------------------------------------------------

POSITIVE_WORDS: frozenset[str] = frozenset(
    {
        "agree",
        "support",
        "approve",
        "accept",
        "favor",
        "positive",
        "benefit",
        "advantage",
        "improve",
        "success",
        "effective",
        "efficient",
        "optimal",
        "excellent",
        "good",
        "great",
        "best",
        "ideal",
        "recommend",
        "endorse",
        "confident",
        "optimistic",
        "progress",
        "gain",
        "win",
        "solution",
        "opportunity",
        "growth",
        "innovation",
        "strength",
        "asset",
        "value",
    }
)

NEGATIVE_WORDS: frozenset[str] = frozenset(
    {
        "disagree",
        "oppose",
        "reject",
        "deny",
        "refuse",
        "negative",
        "risk",
        "disadvantage",
        "worsen",
        "failure",
        "ineffective",
        "inefficient",
        "poor",
        "bad",
        "worst",
        "problem",
        "issue",
        "concern",
        "worry",
        "doubt",
        "skeptical",
        "pessimistic",
        "loss",
        "lose",
        "threat",
        "weakness",
        "liability",
        "cost",
        "burden",
        "challenge",
        "obstacle",
        "barrier",
        "resistance",
        "objection",
        "criticism",
        "flaw",
        "defect",
    }
)

# ---------------------------------------------------------------------------
# Proposal detection patterns
# ---------------------------------------------------------------------------

PROPOSAL_PATTERNS: list[str] = [
    r"propose\w*\s+(?:that\s+)?(?:we\s+)?(.{10,100}?)(?:\.|$|\n)",
    r"suggest\w*\s+(?:that\s+)?(?:we\s+)?(.{10,100}?)(?:\.|$|\n)",
    r"recommend\w*\s+(?:that\s+)?(?:we\s+)?(.{10,100}?)(?:\.|$|\n)",
    r"move\s+(?:that\s+)?(?:we\s+)?(.{10,100}?)(?:\.|$|\n)",
]

# ---------------------------------------------------------------------------
# Decision outcome patterns
# ---------------------------------------------------------------------------

APPROVAL_PATTERNS: list[str] = [
    r"(?:approved?|accepted?|adopted?|agreed?|passed)",
    r"(?:we\s+(?:will|shall)\s+(?:proceed|move\s+forward|implement))",
    r"(?:consensus\s+(?:reached|achieved))",
    r"(?:unanimous\s+(?:support|approval))",
]

REJECTION_PATTERNS: list[str] = [
    r"(?:rejected?|denied?|declined?|opposed?|vetoed)",
    r"(?:we\s+(?:will\s+not|cannot)\s+(?:proceed|move\s+forward|implement))",
    r"(?:no\s+(?:consensus|agreement))",
    r"(?:tabled?|postponed?|deferred)",
]

# ---------------------------------------------------------------------------
# Policy extraction patterns (used in compliance violation detection)
# ---------------------------------------------------------------------------

POLICY_EXTRACTION_PATTERNS: list[str] = [
    r"(?:you must|you should|always|never|priority|ensure|maintain)" r"\s+(.{10,150}?)(?:\.|$|\n)",
    r"(?:objective|goal|mandate|responsibility):?" r"\s*(.{10,150}?)(?:\.|$|\n)",
]

# Negation words used when detecting policy contradictions
NEGATION_WORDS: frozenset[str] = frozenset(
    {
        "never",
        "no",
        "not",
        "don't",
        "won't",
        "shouldn't",
        "mustn't",
    }
)

# Common English stop words excluded from key-term extraction
STOP_WORDS: frozenset[str] = frozenset(
    {
        "the",
        "a",
        "an",
        "and",
        "or",
        "but",
        "in",
        "on",
        "at",
        "to",
        "for",
        "of",
        "with",
        "by",
        "you",
        "must",
        "should",
        "always",
        "never",
    }
)

# ---------------------------------------------------------------------------
# Coalition detection keywords
# ---------------------------------------------------------------------------

ALIGNMENT_KEYWORDS: list[str] = [
    "agree with",
    "support",
    "join",
    "together",
    "aligned",
    "same page",
    "united",
]

# Stop words for coalition topic extraction
COALITION_STOP_WORDS: frozenset[str] = frozenset(
    {
        "the",
        "a",
        "an",
        "and",
        "or",
        "but",
        "in",
        "on",
        "at",
        "to",
        "for",
        "of",
        "with",
        "by",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "could",
        "should",
        "may",
        "might",
        "must",
        "can",
        "this",
        "that",
        "these",
        "those",
        "i",
        "you",
        "he",
        "she",
        "it",
        "we",
        "they",
        "me",
        "him",
        "her",
        "us",
        "them",
        "my",
        "your",
        "his",
        "its",
        "our",
        "their",
    }
)

# Minimum coalition size (number of agents required to count as a coalition)
MIN_COALITION_SIZE: int = 3

# ---------------------------------------------------------------------------
# Turning-point detection thresholds
# ---------------------------------------------------------------------------

# Minimum absolute sentiment shift (0–1) to classify a transition as a turning point
TURNING_POINT_THRESHOLD: float = 0.3
TURNING_POINT_HIGH_THRESHOLD: float = 0.5
TURNING_POINT_MEDIUM_THRESHOLD: float = 0.4

# ---------------------------------------------------------------------------
# Outcome normalization maps
# ---------------------------------------------------------------------------

APPROVED_OUTCOMES: frozenset[str] = frozenset(
    {
        "approved",
        "accepted",
        "adopted",
        "passed",
        "for",
    }
)

REJECTED_OUTCOMES: frozenset[str] = frozenset(
    {
        "rejected",
        "denied",
        "declined",
        "opposed",
        "against",
    }
)
