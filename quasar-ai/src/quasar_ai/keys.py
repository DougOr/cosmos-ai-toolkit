"""Stable document-id derivation from cache keys."""

import hashlib


def doc_id(key: str) -> str:
    """Map a cache key to a fixed-size document id.

    sha256 (v1 used md5); stable so the same key always hits the same document.
    """
    return hashlib.sha256(key.encode("utf-8")).hexdigest()
