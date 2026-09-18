"""TTL presets shared with the v1 harness so results stay comparable."""

from enum import StrEnum


class TTLPreset(StrEnum):
    INDEFINITE = "indefinite"
    MIN_1 = "1min"
    MIN_2 = "2min"
    MIN_5 = "5min"
    MIN_15 = "15min"
    MIN_30 = "30min"
    HOUR_1 = "1hour"
    HOUR_6 = "6hours"
    HOUR_24 = "24hours"


TTL_PRESET_SECONDS: dict[str, int] = {
    TTLPreset.INDEFINITE: -1,  # Cosmos DB: ttl = -1 means the item never expires
    TTLPreset.MIN_1: 60,
    TTLPreset.MIN_2: 120,
    TTLPreset.MIN_5: 300,
    TTLPreset.MIN_15: 900,
    TTLPreset.MIN_30: 1800,
    TTLPreset.HOUR_1: 3600,
    TTLPreset.HOUR_6: 21600,
    TTLPreset.HOUR_24: 86400,
}


def resolve_ttl(ttl_preset: str | None = None, ttl_seconds: int | None = None) -> int | None:
    """Resolve a TTL value from a preset and/or explicit seconds.

    Presets take precedence over explicit seconds (v1 behaviour kept).
    Returns None when neither is given (caller decides the default).
    """
    if ttl_preset:
        return TTL_PRESET_SECONDS.get(ttl_preset, ttl_seconds)
    return ttl_seconds
