"""Offline lexical embeddings + cosine similarity.

The hash embedder is deterministic, dependency-free, and *lexical*: it hashes
words and char-trigrams, so rephrasings that share vocabulary score well and
paraphrases in different words score poorly. It is labeled `hash-lexical`
everywhere it appears - true semantic embeddings arrive by switching
EMBEDDING_PROVIDER=ollama (still 100% local, e.g. nomic-embed-text).

The emulator has no native vector search, so similarity is computed
app-side over recent entries (see docs/CLOUD_DELTAS.md).
"""

import hashlib
import math
import re

TOKEN_RE = re.compile(r"[a-z0-9]+")


def hash_embedding(text: str, dim: int = 512) -> list[float]:
    """Deterministic bag-of-words + char-trigram hashing, L2-normalized."""
    vector = [0.0] * dim
    tokens = TOKEN_RE.findall(text.lower())

    grams: list[str] = list(tokens)
    for token in tokens:
        padded = f"^{token}$"
        grams.extend(padded[i : i + 3] for i in range(len(padded) - 2))

    for gram in grams:
        digest = hashlib.sha256(gram.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % dim
        sign = 1.0 if digest[4] & 1 else -1.0
        vector[index] += sign

    norm = math.sqrt(sum(v * v for v in vector)) or 1.0
    return [round(v / norm, 6) for v in vector]


def cosine(a: list[float], b: list[float]) -> float:
    """Cosine of normalized vectors = dot product. 0.0 on any mismatch."""
    if not a or len(a) != len(b):
        return 0.0
    return round(sum(x * y for x, y in zip(a, b)), 6)
