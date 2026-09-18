"""Canonical request hashing + lexical embeddings."""

from nebula_mind.embeddings import cosine, hash_embedding
from nebula_mind.keys import request_hash


def test_hash_covers_every_answer_changing_param():
    base = request_hash("q", "s", "m", 0.7, 100)
    assert request_hash("q", "s", "m", 0.7, 100) == base  # identical
    assert request_hash("different", "s", "m", 0.7, 100) != base
    assert request_hash("q", "other-system", "m", 0.7, 100) != base
    assert request_hash("q", "s", "other-model", 0.7, 100) != base
    assert request_hash("q", "s", "m", 0.9, 100) != base
    assert request_hash("q", "s", "m", 0.7, 200) != base


def test_float_noise_is_normalized():
    assert request_hash("q", None, "m", 0.7, 100) == request_hash("q", None, "m", 0.7000001, 100)


def test_none_and_empty_system_prompt_equivalent():
    assert request_hash("q", None, "m", 0.7, 100) == request_hash("q", "", "m", 0.7, 100)


def test_hash_embedding_is_unit_norm_and_deterministic():
    a = hash_embedding("explain quantum computing simply", dim=256)
    b = hash_embedding("explain quantum computing simply", dim=256)
    assert a == b
    assert abs(sum(v * v for v in a) - 1.0) < 1e-3


def test_related_text_scores_higher_than_unrelated():
    dim = 512
    base = hash_embedding("explain quantum computing in simple terms", dim)
    rephrased = hash_embedding("quantum computing explained in simple terms", dim)
    unrelated = hash_embedding("chocolate cake recipe with butter and sugar", dim)
    assert cosine(base, rephrased) > cosine(base, unrelated)
    assert cosine(base, rephrased) > 0.3
    assert abs(cosine(base, base) - 1.0) < 1e-3


def test_cosine_handles_mismatch():
    assert cosine([], []) == 0.0
    assert cosine([1.0], [1.0, 0.0]) == 0.0
