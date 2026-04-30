# tests/test_embedder_sentence_transformers.py
from research_keeper.adapters.embedder.sentence_transformers import (
    SentenceTransformerEmbedder,
)


def test_embed_returns_correct_size():
    """Embedding should return 768 floats × 4 bytes = 3072 bytes."""
    embedder = SentenceTransformerEmbedder()
    result = embedder.embed("test content")
    assert len(result) == 3072, f"Expected 3072 bytes, got {len(result)}"


def test_embed_returns_empty_on_error():
    """Embedder should return b"" on failure, not raise."""
    embedder = SentenceTransformerEmbedder()
    # Force error by mocking model to raise
    embedder._model = None
    embedder._model_name = "nonexistent-model-xyz"
    result = embedder.embed("test")
    assert result == b"", f"Expected b'' on error, got {result!r}"


def test_embedding_quality():
    """Similar texts should have higher cosine similarity than unrelated texts."""
    import numpy as np

    embedder = SentenceTransformerEmbedder()

    # Similar texts
    emb1 = embedder.embed("The cat sat on the mat")
    emb2 = embedder.embed("A cat sitting on a rug")

    # Unrelated text
    emb3 = embedder.embed("The weather is nice today")

    def cosine_sim(a: bytes, b: bytes) -> float:
        a_vec = np.frombuffer(a, dtype=np.float32)
        b_vec = np.frombuffer(b, dtype=np.float32)
        return float(
            np.dot(a_vec, b_vec) / (np.linalg.norm(a_vec) * np.linalg.norm(b_vec))
        )

    sim_similar = cosine_sim(emb1, emb2)
    sim_unrelated = cosine_sim(emb1, emb3)

    assert sim_similar > sim_unrelated, (
        f"Similar texts should have higher similarity: "
        f"similar={sim_similar:.3f}, unrelated={sim_unrelated:.3f}"
    )
    assert sim_similar > 0.5, (
        f"Similar texts should have sim > 0.5, got {sim_similar:.3f}"
    )


def test_embed_batch_returns_correct_size():
    """embed_batch should return one packed array per input string."""
    embedder = SentenceTransformerEmbedder()
    contents = ["first chunk", "second chunk", "third piece"]
    results = embedder.embed_batch(contents)
    assert len(results) == 3, f"Expected 3 results, got {len(results)}"
    for r in results:
        assert len(r) == 3072, f"Expected 3072 bytes, got {len(r)}"


def test_embed_batch_preserves_ordering():
    """First input maps to first output, etc."""
    embedder = SentenceTransformerEmbedder()
    import numpy as np

    a_text = "quantum computing breakthroughs in silicon photonics"
    b_text = "Italian Renaissance painting techniques and patronage"
    a_emb, b_emb = embedder.embed_batch([a_text, b_text])
    a_vec = np.frombuffer(a_emb, dtype=np.float32)
    b_vec = np.frombuffer(b_emb, dtype=np.float32)
    sim = float(np.dot(a_vec, b_vec) / (np.linalg.norm(a_vec) * np.linalg.norm(b_vec)))
    assert sim < 0.6, f"Unrelated texts should have low similarity, got {sim:.3f}"


def test_embed_batch_handles_single_item():
    """Single-item batch returns one result."""
    embedder = SentenceTransformerEmbedder()
    results = embedder.embed_batch(["single chunk"])
    assert len(results) == 1
    assert len(results[0]) == 3072


def test_embed_batch_handles_empty_list():
    """Empty list returns empty list."""
    embedder = SentenceTransformerEmbedder()
    results = embedder.embed_batch([])
    assert results == []
