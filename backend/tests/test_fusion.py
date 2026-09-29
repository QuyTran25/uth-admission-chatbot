import pytest
from app.services.retrieval_service import (
    _min_max_normalize,
    _fuse_weighted,
    _fuse_rrf,
    ScoredChunk,
)

def make_chunk(cid: str, score: float, text: str = "") -> ScoredChunk:
    return ScoredChunk(
        chunk_id=cid,
        score=score,
        text=text,
        admission_year=2026,
        program_type="standard",
        section_name="general",
        source_file="test.pdf",
        source_urls=[],
        extra_urls=[],
    )

def test_min_max_normalize():
    scores = [10.0, 20.0, 30.0]
    normed = _min_max_normalize(scores)
    assert normed[0] == pytest.approx(0.0)
    assert normed[1] == pytest.approx(0.5)
    assert normed[2] == pytest.approx(1.0)

def test_min_max_normalize_single_or_flat():
    scores = [15.0, 15.0]
    normed = _min_max_normalize(scores)
    assert normed == [1.0, 1.0]

def test_fuse_weighted_arithmetic():
    bm25 = [make_chunk("c1", 10.0), make_chunk("c2", 20.0)]
    dense = [make_chunk("c1", 0.8), make_chunk("c2", 0.4)]

    # alpha=0.4 (dense=0.4, bm25=0.6)
    # dense: c1 -> 1.0, c2 -> 0.0
    # bm25: c1 -> 0.0, c2 -> 1.0
    # score(c1) = 0.4 * 1.0 + 0.6 * 0.0 = 0.4
    # score(c2) = 0.4 * 0.0 + 0.6 * 1.0 = 0.6
    # c2 rank 1, c1 rank 2
    fused = _fuse_weighted(bm25, dense, alpha=0.4)
    assert len(fused) == 2
    assert fused[0].chunk_id == "c2"
    assert fused[0].score == pytest.approx(0.6)
    assert fused[1].chunk_id == "c1"
    assert fused[1].score == pytest.approx(0.4)

def test_fuse_rrf():
    bm25 = [make_chunk("c1", 20.0), make_chunk("c2", 10.0)]
    dense = [make_chunk("c2", 0.9), make_chunk("c1", 0.5)]

    # k=60
    # c1: rank 1 in bm25, rank 2 in dense -> 1/(60+1) + 1/(60+2) = 1/61 + 1/62
    # c2: rank 2 in bm25, rank 1 in dense -> 1/(60+2) + 1/(60+1) = 1/62 + 1/61 (equal)
    fused = _fuse_rrf(bm25, dense)
    assert len(fused) == 2
    assert {f.chunk_id for f in fused} == {"c1", "c2"}
