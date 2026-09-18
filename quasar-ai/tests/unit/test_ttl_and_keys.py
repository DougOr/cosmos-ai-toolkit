"""TTL preset resolution and key hashing (pure unit, no I/O)."""

from quasar_ai.keys import doc_id
from quasar_ai.ttl import TTLPreset, resolve_ttl


def test_preset_values_match_v1_harness():
    # Same table as the v1 harness so benchmark results stay comparable.
    assert resolve_ttl("2min") == 120
    assert resolve_ttl("5min") == 300
    assert resolve_ttl("1hour") == 3600
    assert resolve_ttl("indefinite") == -1


def test_preset_takes_precedence_over_seconds():
    assert resolve_ttl("5min", 9999) == 300


def test_seconds_only():
    assert resolve_ttl(None, 42) == 42


def test_unresolved_returns_none():
    assert resolve_ttl(None, None) is None


def test_unknown_preset_falls_back_to_seconds():
    assert resolve_ttl("nonsense", 77) == 77


def test_doc_id_is_stable_sha256():
    assert doc_id("same-key") == doc_id("same-key")
    assert len(doc_id("k")) == 64  # sha256 hex digest, unlike v1's md5
    assert doc_id("a") != doc_id("b")


def test_ttl_preset_enum_is_string():
    assert TTLPreset.MIN_2 == "2min"
