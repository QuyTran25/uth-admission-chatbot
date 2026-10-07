"""
test_pipeline_decision.py — Kiểm thử đơn vị cho Single Source of Truth (SSoT) pipeline_decision
Đảm bảo luồng quyết định 3 lớp đồng nhất giữa chat.py và pipeline_union_eval.py.
"""

from unittest.mock import MagicMock, patch
import pytest

from app.services.pipeline_decision import decide_query, DecisionResult, apply_gate
from app.services.retrieval_service import ScoredChunk


def test_decide_query_layer1_year_filter_refusal():
    """Lớp 1: Từ khóa OOS tại tầng year_filter -> Từ chối ngay lập tức."""
    res = decide_query("Dự đoán điểm chuẩn ngành Công nghệ thông tin năm 2026?")
    assert res.status == "refused"
    assert res.refusal_source == "year_filter"
    assert len(res.chunks) == 0


def test_decide_query_layer1_year_filter_fallback():
    """Lớp 1: Năm ngoài [2022, 2026] -> fallback_warning về 2026 kèm cảnh báo."""
    mock_retriever = MagicMock(return_value=([], {}))
    res = decide_query(
        "Học phí ngành CNTT năm 2015 là bao nhiêu?",
        retriever_fn=mock_retriever,
    )
    assert res.behavior == "fallback_warning"
    assert res.is_fallback is True
    assert res.filter_year == 2026
    assert "2015" in res.message


def test_decide_query_layer1_year_filter_clarify():
    """Lớp 1: So sánh nhiều năm -> Yêu cầu làm rõ năm."""
    res = decide_query("So sánh điểm chuẩn năm 2024 và 2025 ngành logistics")
    assert res.behavior == "clarify"


def test_decide_query_layer2_oos_filter():
    """Lớp 2: Câu hỏi out-of-scope (trường khác, bói toán,...) -> Từ chối ngay."""
    res = decide_query("Điểm chuẩn Trường Đại học Bách Khoa TP.HCM năm 2024?")
    assert res.status == "refused"
    assert res.refusal_source == "oos_filter"
    assert len(res.chunks) == 0


def test_decide_query_layer3_gate_disabled():
    """Lớp 3: Khi gate_enabled=False (mặc định an toàn), truy vấn hợp lệ luôn proceed."""
    mock_chunks = [
        ScoredChunk(
            chunk_id="c1",
            text="Học phí 2026 là 15 triệu",
            score=0.45,
            score_raw=0.45,
            source_file="hoc_phi_2026.pdf",
            program_type="chuẩn",
            admission_year=2026,
            section_name="Học phí",
            source_urls=[],
            extra_urls=[],
        )
    ]
    mock_meta = {"dense_top1_score": 0.45, "dense_top2_score": 0.40, "has_consensus": False}

    mock_retriever = MagicMock(return_value=(mock_chunks, mock_meta))

    res = decide_query(
        query="Học phí UTH năm 2026 là bao nhiêu?",
        top_k=5,
        gate_enabled=False,
        retriever_fn=mock_retriever,
    )

    assert res.status == "proceed"
    assert res.refusal_source is None
    assert len(res.chunks) == 1
    mock_retriever.assert_called_once()


def test_decide_query_layer3_gate_enabled_refuse():
    """Lớp 3: Khi gate_enabled=True và điểm retriever thấp -> Bị Gate chặn."""
    mock_chunks = [
        ScoredChunk(
            chunk_id="c1",
            text="Thông tin không liên quan",
            score=0.30,
            score_raw=0.30,
            source_file="f1.pdf",
            program_type="chuẩn",
            admission_year=2026,
            section_name="Khác",
            source_urls=[],
            extra_urls=[],
        )
    ]
    mock_meta = {"dense_top1_score": 0.30, "dense_top2_score": 0.25, "has_consensus": False}
    mock_retriever = MagicMock(return_value=(mock_chunks, mock_meta))

    gate_cfg = {
        "enabled": True,
        "threshold_default": 0.60,
        "threshold_consensus": 0.50,
        "consensus_type": "file",
        "margin_threshold": None,
    }

    res = decide_query(
        query="Quy định bảo lưu kết quả học tập thế nào?",
        top_k=5,
        gate_enabled=True,
        gate_config=gate_cfg,
        retriever_fn=mock_retriever,
    )

    assert res.status == "refused"
    assert res.refusal_source == "retrieval_gate"
    assert "tài liệu" in res.message.lower() or "không tìm thấy" in res.message.lower() or "chưa có" in res.message.lower()


def test_decide_query_layer3_gate_enabled_pass():
    """Lớp 3: Khi gate_enabled=True và điểm retriever cao -> Vượt qua Gate thành công."""
    mock_chunks = [
        ScoredChunk(
            chunk_id="c1",
            text="Chỉ tiêu ngành CNTT là 500",
            score=0.75,
            score_raw=0.75,
            source_file="f1.pdf",
            program_type="chuẩn",
            admission_year=2026,
            section_name="Chỉ tiêu",
            source_urls=[],
            extra_urls=[],
        )
    ]
    mock_meta = {"dense_top1_score": 0.75, "dense_top2_score": 0.70, "has_consensus": True}
    mock_retriever = MagicMock(return_value=(mock_chunks, mock_meta))

    gate_cfg = {
        "enabled": True,
        "threshold_default": 0.60,
        "threshold_consensus": 0.50,
        "consensus_type": "file",
        "margin_threshold": None,
    }

    res = decide_query(
        query="Chỉ tiêu ngành CNTT năm 2026?",
        top_k=5,
        gate_enabled=True,
        gate_config=gate_cfg,
        retriever_fn=mock_retriever,
    )

    assert res.status == "proceed"
    assert res.refusal_source is None
    assert len(res.chunks) == 1


def test_decide_query_calls_real_retriever_with_enable_boost():
    """Kiểm tra gọi chữ ký retriever thật có nhận enable_boost."""
    with patch("app.services.retrieval_service.search_hybrid") as mock_hybrid:
        mock_hybrid.return_value = ([], {})
        res = decide_query(
            query="Học phí năm 2026?",
            top_k=5,
            gate_enabled=False,
            enable_boost=True,
        )
        assert res.status == "proceed"
        mock_hybrid.assert_called_once()
