"""Mock LLM determinism - reproducible benchmarks depend on it."""

from quasar_ai.generators import MockLLM


async def test_same_prompt_same_content():
    mock = MockLLM(latency_seconds=0.0)
    a = await mock.generate("Explain quantum computing")
    b = await mock.generate("Explain quantum computing")
    assert a["content"] == b["content"]
    assert a["usage"] == b["usage"]


async def test_different_prompt_different_content():
    mock = MockLLM(latency_seconds=0.0)
    a = await mock.generate("prompt one")
    b = await mock.generate("prompt two")
    assert a["content"] != b["content"]


async def test_system_prompt_changes_seed():
    mock = MockLLM(latency_seconds=0.0)
    a = await mock.generate("q", system_prompt="be brief")
    b = await mock.generate("q", system_prompt="be verbose")
    assert a["content"] != b["content"]


async def test_generate_for_key_adapter():
    mock = MockLLM(latency_seconds=0.0)
    payload = await mock.generate_for_key("some-key")
    assert "some-key" in payload["content"]
