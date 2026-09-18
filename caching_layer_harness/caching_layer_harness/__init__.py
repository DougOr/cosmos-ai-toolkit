"""
Azure Cosmos DB Caching Layer Harness
A production-ready caching system for LLM prompts and generic JSON data
"""

__version__ = "1.0.0"

from .app import app

__all__ = ["app"]
