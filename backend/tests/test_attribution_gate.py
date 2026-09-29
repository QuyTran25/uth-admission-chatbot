import pytest
from app.services.attribution_gate import (
    check_attribution,
    build_citation_list,
    compute_lexical_support,
)
from app.services.retrieval_service import ScoredChunk

def make_chunk(cid: str, text: str = "") -> ScoredChunk:
    return ScoredChunk(
        chunk_id=cid,
        score=0.9,
        text=text,
        admission_year=2026,
        program_type="standard",
        section_name="general",
        source_file="test.pdf",
        source_urls=["https://tuyensinh.ut.edu.vn"],
        extra_urls=[],
    )

def test_attribution_valid_citations():
    """Tất cả cited_ids đều có trong retrieved chunks và text có lexical support."""
    c1 = make_chunk("c1", "Ngành Công nghệ thông tin có chỉ tiêu là 300 sinh viên.")
    c2 = make_chunk("c2", "Học phí chương trình chuẩn là 35 triệu đồng.")
    retrieved = [c1, c2]

    res = check_attribution(
        cited_ids=["c1"],
        retrieved_chunks=retrieved,
        response_text="Chỉ tiêu ngành Công nghệ thông tin là 300 sinh viên theo quyết định tuyển sinh.",
        is_refused=False,
    )
    assert res.passed is True
    assert res.citation_precision == 1.0
    assert res.total_citations == 1
    assert res.valid_citations == 1
    assert len(res.failed_citations) == 0

def test_attribution_hallucinated_chunk_id():
    """Gemini trích dẫn chunk_id không hề có trong kết quả retrieve -> Fail."""
    c1 = make_chunk("c1", "Thông tin hợp lệ.")
    retrieved = [c1]

    res = check_attribution(
        cited_ids=["fake_c999"],
        retrieved_chunks=retrieved,
        response_text="Thông tin tuyển sinh năm 2026.",
        is_refused=False,
    )
    assert res.passed is False
    assert res.citation_precision == 0.0
    assert "fake_c999" in res.failed_citations

def test_attribution_empty_citation():
    """Gemini không trích dẫn gì cả -> Fail."""
    c1 = make_chunk("c1", "Nội dung.")
    res = check_attribution(
        cited_ids=[],
        retrieved_chunks=[c1],
        response_text="Câu trả lời không trích dẫn.",
        is_refused=False,
    )
    assert res.passed is False
    assert res.total_citations == 0

def test_attribution_refusal_bypass():
    """Câu hỏi bị từ chối -> bypass attribution check và đánh dấu rõ ràng."""
    res = check_attribution(
        cited_ids=[],
        retrieved_chunks=[],
        response_text="Không hỗ trợ",
        is_refused=True,
    )
    assert res.passed is True
    assert res.is_refusal_bypassed is True
    assert res.method == "bypassed_refusal"

def test_build_citation_list_filters_invalid():
    """Chỉ xuất ra trích dẫn hợp lệ."""
    c1 = make_chunk("c1", "Nội dung 1")
    retrieved = [c1]

    citations = build_citation_list(["c1", "invalid_chunk"], retrieved)
    assert len(citations) == 1
    assert citations[0]["chunk_id"] == "c1"
