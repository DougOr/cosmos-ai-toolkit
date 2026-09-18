"""NebulaMind - real-LLM semantic cache on Azure Cosmos DB.

Exact hits by content hash, similarity hits by app-side cosine, pluggable
LLM + embedding providers (mock / Ollama / OpenAI-compatible). 100% local on
the Cosmos DB emulator with the default mock + lexical-hash providers.
"""

from nebula_mind.config import Settings, get_settings
from nebula_mind.embeddings import cosine, hash_embedding
from nebula_mind.keys import request_hash

__version__ = "0.1.0"

__all__ = ["Settings", "get_settings", "request_hash", "hash_embedding", "cosine", "__version__"]
