from __future__ import annotations

import re

ISO_8601_DURATION = re.compile(
    r"^P(?:(\d+)Y)?(?:(\d+)M)?(?:(\d+)D)?"
    r"(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?)?$"
)


def parse_iso8601_duration(value: str | None) -> int | None:
    """Parse an ISO 8601 duration string to total seconds.

    Handles YouTube's format: PT1H2M30S, PT3M5S, PT45S, etc.
    Returns None for unparseable or None input.
    """
    if not value:
        return None

    match = ISO_8601_DURATION.match(value)
    if not match:
        return None

    parts = match.groups()
    years = int(parts[0]) if parts[0] else 0
    months = int(parts[1]) if parts[1] else 0
    days = int(parts[2]) if parts[2] else 0
    hours = int(parts[3]) if parts[3] else 0
    minutes = int(parts[4]) if parts[4] else 0
    seconds = int(float(parts[5])) if parts[5] else 0

    total = seconds
    total += minutes * 60
    total += hours * 3600
    total += days * 86400
    total += months * 2_592_000  # approximate (30.44 days)
    total += years * 31_536_000  # approximate (365.25 days)

    return total
