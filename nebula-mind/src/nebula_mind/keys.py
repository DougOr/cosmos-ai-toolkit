"""Canonical request hashing: the exact-match key of the semantic cache.

The hash covers EVERYTHING that changes the answer - prompt, system prompt,
model, temperature, max_tokens - so a cache hit is guaranteed to be the
answer you would have gotten (v1 hashed only a user-supplied key label).
"""

import hashlib
import json


def request_hash(
    prompt: str,
    system_prompt: str | None = None,
    model: str = "default",
    temperature: float = 0.7,
    max_tokens: int = 1000,
) -> str:
    canonical = json.dumps(
        {
            "prompt": prompt,
            "system": system_prompt or "",
            "model": model,
            # round away float noise: 0.7 and 0.70000001 are the same request
            "temperature": round(temperature, 3),
            "max_tokens": int(max_tokens),
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
