"""Shared test fixtures. Emulator integration tests self-skip when it is down."""

import warnings

import httpx
import pytest

from quasar_ai.config import WELL_KNOWN_EMULATOR_KEY


def _emulator_up() -> bool:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            # Any HTTP response at all means the emulator listener is up.
            httpx.get("https://localhost:8081/", verify=False, timeout=1.5)
        return True
    except Exception:  # noqa: BLE001
        return False


EMULATOR_UP = _emulator_up()

requires_emulator = pytest.mark.skipif(
    not EMULATOR_UP,
    reason="Azure Cosmos DB emulator not reachable on https://localhost:8081",
)


def emulator_settings():
    from quasar_ai.config import Settings

    return Settings(
        cosmos_endpoint="https://localhost:8081/",
        cosmos_key=WELL_KNOWN_EMULATOR_KEY,
        database_name="QuasarTestDB",
        intelligent_container="t-intelligent",
        generic_container="t-generic",
        simulated_latency_seconds=0.0,
    )
