"""Shared input-bound helpers for simulation configuration validators."""


def validate_int_bounds(
    value: int,
    *,
    minimum: int,
    maximum: int,
    field_name: str,
) -> int:
    """Require ``minimum <= value <= maximum``; raise ``ValueError`` with field-specific messages."""
    if value < minimum:
        raise ValueError(f"{field_name} must be >= {minimum}")
    if value > maximum:
        raise ValueError(f"{field_name} must be <= {maximum}")
    return value
