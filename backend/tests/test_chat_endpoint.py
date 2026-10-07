"""
test_chat_endpoint.py — Kiểm thử FastAPI endpoint /api/v1/chat với SSoT pipeline_decision
"""

from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.generator import GenerationResult
from app.services.retrieval_service import ScoredChunk

client = TestClient(app)


def test_chat_refused_out_of_scope():
    """Truy vấn out-of-scope bị từ chối sớm ở tầng tiền sinh, không gọi Gemini."""
    with patch("app.api.endpoints.chat.generate_answer") as mock_gen:
        resp = client.post(
            "/api/v1/chat",
            json={"query": "Điểm chuẩn trường Đại học Bách Khoa TP.HCM năm 2024?"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["behavior"] == "refused"
        assert data["refused_reason"] == "out_of_scope"
        assert len(data["citations"]) == 0
        mock_gen.assert_not_called()


def test_chat_clarify_multi_year():
    """Truy vấn cần làm rõ năm trả về behavior='clarify', không gọi Gemini."""
    with patch("app.api.endpoints.chat.generate_answer") as mock_gen:
        resp = client.post(
            "/api/v1/chat",
            json={"query": "So sánh điểm chuẩn năm 2024 và 2025 ngành logistics"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["behavior"] == "clarify"
        mock_gen.assert_not_called()


def test_chat_success_with_generation():
    """Truy vấn hợp lệ đi qua đầy đủ: decide_query -> generate_answer -> attribution_gate."""
    mock_chunks = [
        ScoredChunk(
            chunk_id="chunk_test_01",
            text="Học phí UTH năm 2026 là 15 triệu/học kỳ.",
            score=0.85,
            score_raw=0.85,
            source_file="hoc_phi_2026.pdf",
            program_type="chuẩn",
            admission_year=2026,
            section_name="Học phí",
            source_urls=["https://tuyensinh.ut.edu.vn"],
            extra_urls=[],
        )
    ]

    mock_gen_result = GenerationResult(
        answer_text="Học phí UTH năm 2026 là 15 triệu/học kỳ [[chunk_test_01]].",
        cited_ids=["chunk_test_01"],
        is_refused=False,
    )

    with patch("app.services.pipeline_decision.retrieve_with_dynamic_routing") as mock_ret, \
         patch("app.api.endpoints.chat.generate_answer", return_value=mock_gen_result) as mock_gen:

        mock_ret.return_value = (mock_chunks, {"dense_top1_score": 0.85})

        resp = client.post(
            "/api/v1/chat",
            json={"query": "Học phí UTH năm 2026 là bao nhiêu?"},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["behavior"] == "answer"
        assert "15 triệu" in data["answer"]
        assert len(data["citations"]) == 1
        assert data["citations"][0]["chunk_id"] == "chunk_test_01"
        assert data["citation_precision"] == 1.0
        mock_gen.assert_called_once()
