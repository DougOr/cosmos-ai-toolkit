"""QuasarAI - async-first Azure Cosmos DB caching engine for LLM workloads.

100% local: runs against the Azure Cosmos DB emulator, zero cloud required.
"""

from quasar_ai.config import Settings, get_settings
from quasar_ai.keys import doc_id
from quasar_ai.ttl import TTLPreset, TTL_PRESET_SECONDS, resolve_ttl

__version__ = "0.1.0"

__all__ = [
    "Settings",
    "get_settings",
    "TTLPreset",
    "TTL_PRESET_SECONDS",
    "resolve_ttl",
    "doc_id",
    "__version__",
]
