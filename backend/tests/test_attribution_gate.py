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
    """Gemini không trích dẫn gì cả và nội dung không grounded -> Fail."""
    c1 = make_chunk("c1", "Nội dung tuyển sinh chuyên biệt.")
    res = check_attribution(
        cited_ids=[],
        retrieved_chunks=[c1],
        response_text="Câu trả lời hoàn toàn xa lạ không có từ vựng hay dữ liệu tương thích.",
        is_refused=False,
    )
    assert res.passed is False
    assert res.total_citations == 0

def test_attribution_missing_tags_but_content_grounded_passes():
    """Gemini quên tag [[chunk_id]] nhưng nội dung được grounded đầy đủ trong 5 chunks -> Pass không chặn oan."""
    c1 = make_chunk("c1", "Điểm chuẩn ngành Công nghệ thông tin năm 2026 là 25.5 điểm.")
    res = check_attribution(
        cited_ids=[],
        retrieved_chunks=[c1],
        response_text="Điểm chuẩn ngành Công nghệ thông tin là 25.5 điểm.",
        is_refused=False,
    )
    assert res.passed is True
    assert res.citation_precision == 0.0
    assert res.method == "content_grounded_missing_tags"

def test_attribution_hallucinated_number_fails():
    """Case 99.000.000 vs 24.000.000: Model bịa đặt số tiền/số liệu không có trong 5 chunks -> Fail."""
    c1 = make_chunk("c1", "Học phí ngành Logistics năm 2026 là 24.000.000 đồng/năm.")
    res = check_attribution(
        cited_ids=["c1"],
        retrieved_chunks=[c1],
        response_text="Học phí ngành Logistics là 99.000.000 đồng/năm [[c1]].",
        is_refused=False,
    )
    assert res.passed is False

def test_attribution_checks_only_top_5_chunks():
    """Chỉ kiểm đúng 5 chunks đưa vào prompt; chunk thứ 6 trở đi không được tính là hợp lệ."""
    chunks = [make_chunk(f"c{i}", f"Nội dung {i}") for i in range(1, 8)]
    res = check_attribution(
        cited_ids=["c6"],
        retrieved_chunks=chunks,
        response_text="Nội dung 6 [[c6]].",
        is_refused=False,
    )
    assert res.passed is False
    assert "c6" in res.failed_citations

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
    assert res.citation_precision is None

def test_build_citation_list_filters_invalid():
    """Chỉ xuất ra trích dẫn hợp lệ."""
    c1 = make_chunk("c1", "Nội dung 1")
    retrieved = [c1]

    citations = build_citation_list(["c1", "invalid_chunk"], retrieved)
    assert len(citations) == 1
    assert citations[0]["chunk_id"] == "c1"
