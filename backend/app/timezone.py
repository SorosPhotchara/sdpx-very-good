"""Ensure timestamps are timezone aware at API boundaries."""

from datetime import UTC, datetime


def as_utc(value: datetime | None) -> datetime | None:
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value
