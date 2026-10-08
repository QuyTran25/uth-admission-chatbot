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


# ---------------------------------------------------------------------------
# CD6 & CD12 Unit Tests
# ---------------------------------------------------------------------------

def test_cd6_config_ssot_weights():
    """CD6: Kiểm tra nguồn sự thật duy nhất (SSoT) của trọng số fusion."""
    from app.core.config import settings
    assert settings.DENSE_WEIGHT == 0.6
    assert settings.BM25_WEIGHT == 0.4
    assert settings.DENSE_WEIGHT + settings.BM25_WEIGHT == pytest.approx(1.0)


def test_cd6_fuse_weighted_preserves_dense_raw_score_for_gate():
    """CD6: _fuse_weighted phải lưu lại điểm cosine gốc của Dense vào score_raw thay vì điểm min-max."""
    bm25 = [make_chunk("c1", 10.0), make_chunk("c2", 20.0)]
    dense = [make_chunk("c1", 0.85), make_chunk("c2", 0.45)]

    # Dense raw: c1=0.85, c2=0.45
    for c in dense:
        c.score_raw = c.score

    fused = _fuse_weighted(bm25, dense, alpha=0.6)
    assert len(fused) == 2
    chunk_by_id = {c.chunk_id: c for c in fused}

    # Retrieval Gate cần điểm cosine gốc để đánh giá chất lượng thực tế
    assert chunk_by_id["c1"].score_raw == pytest.approx(0.85)
    assert chunk_by_id["c2"].score_raw == pytest.approx(0.45)
    # Trong khi điểm score là điểm kết hợp sau min-max
    assert chunk_by_id["c1"].score != chunk_by_id["c1"].score_raw


def test_cd6_fuse_rrf_preserves_dense_raw_score_for_gate():
    """CD6: _fuse_rrf cũng phải duy trì điểm thô gốc cho Retrieval Gate."""
    bm25 = [make_chunk("c1", 15.0), make_chunk("c2", 5.0)]
    dense = [make_chunk("c1", 0.77), make_chunk("c2", 0.33)]
    for c in dense:
        c.score_raw = c.score

    fused = _fuse_rrf(bm25, dense)
    chunk_by_id = {c.chunk_id: c for c in fused}
    assert chunk_by_id["c1"].score_raw == pytest.approx(0.77)
    assert chunk_by_id["c2"].score_raw == pytest.approx(0.33)


def test_cd6_dynamic_routing_filter_mode_preserves_score_raw(monkeypatch):
    """CD6: Trong retrieve_with_dynamic_routing (Filter Mode), score_raw không bị ghi đè bởi score."""
    from app.services import retrieval_service

    fake_chunk = make_chunk("c1", score=0.92)
    fake_chunk.score_raw = 0.81  # Điểm cosine gốc

    def mock_search_hybrid(query, top_k, filters, fusion_method, alpha):
        return [fake_chunk], {"mode": "filtered"}

    monkeypatch.setattr(retrieval_service, "search_hybrid", mock_search_hybrid)

    chunks, _ = retrieval_service.retrieve_with_dynamic_routing("query", filter_year=2024, top_k=1)
    assert len(chunks) == 1
    assert chunks[0].score_raw == pytest.approx(0.81)


def test_cd6_dynamic_routing_boost_mode_preserves_score_raw_before_boost(monkeypatch):
    """CD6: Trong retrieve_with_dynamic_routing (No-filter + Boost), score_raw lưu điểm trước khi boost 1.2x."""
    from app.services import retrieval_service

    chunk_2026 = make_chunk("c_2026", score=0.50)
    chunk_2026.admission_year = 2026
    chunk_2026.score_raw = 0.50

    def mock_search_hybrid(query, top_k, filters, fusion_method, alpha):
        return [chunk_2026], {"mode": "all"}

    monkeypatch.setattr(retrieval_service, "search_hybrid", mock_search_hybrid)

    chunks, _ = retrieval_service.retrieve_with_dynamic_routing("query", filter_year=None, enable_boost=True)
    assert len(chunks) == 1
    assert chunks[0].score == pytest.approx(0.60)      # 0.50 * 1.2
    assert chunks[0].score_raw == pytest.approx(0.50)  # Bảo tồn unboosted score


def test_cd12_search_dense_searches_full_ntotal_when_filtered(monkeypatch):
    """CD12: Khi có bộ lọc metadata, search_dense phải quét trên toàn bộ ntotal vector của FAISS index."""
    import numpy as np
    from app.core.index_store import index_store
    from app.services import retrieval_service

    # Tạo mock meta và faiss_index
    mock_meta = [
        {"faiss_id": 0, "chunk_id": "c_2026_1", "admission_year": 2026, "text": "t1"},
        {"faiss_id": 1, "chunk_id": "c_2026_2", "admission_year": 2026, "text": "t2"},
        {"faiss_id": 2, "chunk_id": "c_2022_1", "admission_year": 2022, "text": "t3"},  # Năm 2022 ở vị trí cuối
    ]

    searched_k_values = []

    class MockFaissIndex:
        ntotal = len(mock_meta)

        def search(self, query_vec, k):
            searched_k_values.append(k)
            # Trả về thứ tự: [0, 1, 2]
            return np.array([[0.9, 0.8, 0.7]], dtype=np.float32), np.array([[0, 1, 2]], dtype=np.int64)

    monkeypatch.setattr(index_store, "_faiss_meta", mock_meta)
    monkeypatch.setattr(index_store, "_faiss_index", MockFaissIndex())
    monkeypatch.setattr(index_store, "_loaded", True)
    monkeypatch.setattr(index_store, "encode_query", lambda q: np.zeros((1, 768), dtype=np.float32))

    # 1. Khi có filter năm 2022 (chỉ có 1 chunk trong 3 chunk):
    results_filtered, _ = retrieval_service.search_dense("query", top_k=1, filters={"admission_year": 2022})
    assert len(results_filtered) == 1
    assert results_filtered[0].chunk_id == "c_2022_1"
    assert results_filtered[0].score_raw == pytest.approx(0.7)
    # CD12: search_k phải bằng faiss_index.ntotal (3), không bị giới hạn bởi top_k * 5
    assert searched_k_values[0] == 3

    # 2. Khi không có filter:
    searched_k_values.clear()
    results_unfiltered, _ = retrieval_service.search_dense("query", top_k=1, filters={"admission_year": "all"})
    assert len(results_unfiltered) == 1
    # Không filter thì dùng min(top_k * 5, ntotal)
    assert searched_k_values[0] == min(1 * 5, 3)


def test_cd6_bm25_only_chunk_does_not_leak_bm25_score_into_score_raw():
    """CD6: Chunk chỉ có ở BM25 không được mang điểm BM25 (thang khác) vào score_raw."""
    bm25 = [make_chunk("c_bm", 15.0), make_chunk("c1", 5.0)]
    dense = [make_chunk("c1", 0.8)]
    for c in dense:
        c.score_raw = c.score

    for fused in (_fuse_weighted(bm25, dense, alpha=0.6), _fuse_rrf(bm25, dense)):
        by_id = {c.chunk_id: c for c in fused}
        assert by_id["c_bm"].score_raw is None
        assert by_id["c_bm"].bm25_raw == pytest.approx(15.0)
        assert by_id["c1"].score_raw == pytest.approx(0.8)


def test_cd6_backfill_dense_raw_computes_true_cosine(monkeypatch):
    """CD6: _backfill_dense_raw bù cosine thật từ FAISS vector cho chunk BM25-only."""
    import numpy as np
    from app.core.index_store import index_store
    from app.services import retrieval_service

    class MockFaissIndex:
        ntotal = 1

        def reconstruct(self, i):
            assert i == 7
            return np.array([1.0, 0.0], dtype=np.float32)

    monkeypatch.setattr(index_store, "_faiss_meta", [{"faiss_id": 7, "chunk_id": "c_bm"}])
    monkeypatch.setattr(index_store, "_faiss_index", MockFaissIndex())
    monkeypatch.setattr(index_store, "_loaded", True)
    monkeypatch.setattr(
        index_store, "encode_query",
        lambda q: np.array([[0.6, 0.8]], dtype=np.float32),
    )

    chunk = make_chunk("c_bm", 0.0)
    chunk.score_raw = None
    retrieval_service._backfill_dense_raw([chunk], "query")
    assert chunk.score_raw == pytest.approx(0.6)  # dot([0.6, 0.8], [1.0, 0.0]) = 0.6


def test_cd6_search_hybrid_backfills_bm25_only_chunk(monkeypatch):
    """CD6: search_hybrid tự động gọi _backfill_dense_raw để bù điểm cosine thật cho BM25-only chunk."""
    import numpy as np
    from app.core.index_store import index_store
    from app.services import retrieval_service

    class MockFaissIndex:
        ntotal = 2

        def reconstruct(self, i):
            if i == 10:
                return np.array([0.8, 0.6], dtype=np.float32)
            return np.array([0.0, 1.0], dtype=np.float32)

    monkeypatch.setattr(index_store, "_faiss_meta", [
        {"faiss_id": 10, "chunk_id": "c_bm_only", "admission_year": 2026, "text": "t1"},
        {"faiss_id": 11, "chunk_id": "c_dense", "admission_year": 2026, "text": "t2"},
    ])
    monkeypatch.setattr(index_store, "_faiss_index", MockFaissIndex())
    monkeypatch.setattr(index_store, "_loaded", True)
    monkeypatch.setattr(
        index_store, "encode_query",
        lambda q: np.array([[0.8, 0.6]], dtype=np.float32),  # dot([0.8, 0.6], [0.8, 0.6]) = 1.0
    )

    chunk_bm = make_chunk("c_bm_only", 25.0)
    chunk_bm.score_raw = 25.0
    chunk_dense = make_chunk("c_dense", 0.7)
    chunk_dense.score_raw = 0.7

    monkeypatch.setattr(retrieval_service, "search_bm25", lambda q, top_k, filters: ([chunk_bm], {}))
    monkeypatch.setattr(retrieval_service, "search_dense", lambda q, top_k, filters: ([chunk_dense], {}))

    results, _ = retrieval_service.search_hybrid("query", top_k=2, fusion_method="weighted")
    res_map = {c.chunk_id: c for c in results}
    assert "c_bm_only" in res_map
    # BM25-only chunk được backfill cosine thật là 1.0, còn bm25_raw là 25.0
    assert res_map["c_bm_only"].score_raw == pytest.approx(1.0)
    assert res_map["c_bm_only"].bm25_raw == pytest.approx(25.0)


def test_cd6_backfill_failsafe_when_reconstruct_unsupported(monkeypatch):
    """CD6: _backfill_dense_raw fail-safe về 0.0 khi reconstruct báo lỗi hoặc không có fid."""
    import numpy as np
    from app.core.index_store import index_store
    from app.services import retrieval_service

    class NoReconstructIndex:
        ntotal = 1

        def reconstruct(self, i):
            raise RuntimeError("direct map not set")

    monkeypatch.setattr(index_store, "_faiss_meta", [{"faiss_id": 3, "chunk_id": "c_bm"}])
    monkeypatch.setattr(index_store, "_faiss_index", NoReconstructIndex())
    monkeypatch.setattr(index_store, "_loaded", True)
    monkeypatch.setattr(
        index_store, "encode_query",
        lambda q: np.array([[1.0, 0.0]], dtype=np.float32),
    )

    # Case 1: reconstruct raise RuntimeError
    chunk1 = make_chunk("c_bm", 0.0)
    chunk1.score_raw = None

    # Case 2: chunk không có trong faiss_meta (fid is None)
    chunk2 = make_chunk("c_unknown", 0.0)
    chunk2.score_raw = None

    retrieval_service._backfill_dense_raw([chunk1, chunk2], "query")
    assert chunk1.score_raw == 0.0  # không crash, fallback an toàn về 0.0
    assert chunk2.score_raw == 0.0  # fid is None cũng an toàn về 0.0




