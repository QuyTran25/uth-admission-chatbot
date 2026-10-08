"""
test_generator.py — Unit test cho generator prompt và structured refusal (CD9 / B2)
"""

from unittest.mock import MagicMock, patch
from app.services.generator import _build_prompt, generate_answer
from app.services.retrieval_service import ScoredChunk


def make_chunk(cid: str, text: str = "Thông tin tuyển sinh.") -> ScoredChunk:
    return ScoredChunk(
        chunk_id=cid,
        score=0.9,
        text=text,
        admission_year=2026,
        program_type="standard",
        section_name="general",
        source_file="test.pdf",
    )


def test_generator_prompt_uses_placeholder_not_fake_ids():
    """Few-shot ví dụ trong prompt phải dùng placeholder cú pháp, không chứa fake chunk IDs."""
    chunks = [make_chunk("2026_test_r001")]
    prompt = _build_prompt("Điểm chuẩn ngành CNTT", chunks, 2026, False)

    # Không được chứa fake chunk id từ thời v1/v2
    assert "2025_diem-chuan_dai-hoc-chinh-quy_t000_r005" not in prompt
    assert "2026_thong-tin-tuyen-sinh_dai-hoc-chinh-quy_t003_r012" not in prompt

    # Chứa hướng dẫn token cấu trúc [STATUS: REFUSED]
    assert "[STATUS: REFUSED]" in prompt


def test_generator_structured_refusal_detection():
    """Khi Gemini trả về [STATUS: REFUSED], generator nhận diện is_refused = True và loại bỏ tag."""
    chunks = [make_chunk("2026_test_r001")]

    with patch("app.services.generator.gemini_client.generate") as mock_gen:
        mock_gen.return_value = "[STATUS: REFUSED] Hiện tại mình chưa có thông tin về câu hỏi này."
        res = generate_answer("Hỏi câu vu vơ", chunks, 2026, False)

    assert res.is_refused is True
    assert "[STATUS: REFUSED]" not in res.answer_text
    assert len(res.cited_ids) == 0


def test_generator_valid_answer_with_citations():
    """Khi Gemini trả lời thành công kèm trích dẫn hợp lệ."""
    chunks = [make_chunk("2026_test_r001")]

    with patch("app.services.generator.gemini_client.generate") as mock_gen:
        mock_gen.return_value = "Điểm chuẩn ngành CNTT là 24.5 [[2026_test_r001]]."
        res = generate_answer("Điểm chuẩn ngành CNTT", chunks, 2026, False)

    assert res.is_refused is False
    assert res.cited_ids == ["2026_test_r001"]
    assert "24.5" in res.answer_text
