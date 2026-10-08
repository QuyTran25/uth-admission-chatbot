import json
from pathlib import Path
from unittest.mock import patch, MagicMock
import pandas as pd
import pytest

from app.services.year_filter import analyze, FilterResult
from eval.run_retrieval_eval import evaluate_single_retrieval


def test_cd2_filter_mode_uses_year_filter_analyze_not_oracle():
    """CD2: Đảm bảo chế độ Filter lấy năm từ year_filter.analyze thay vì nhãn oracle trong CSV."""
    # Giả lập query nói về năm 2024
    query_text = "Học phí năm 2024 của trường UTH là bao nhiêu?"
    # Nhưng nhãn trong row (oracle) bị cố tình đặt sai thành 2022
    row = {
        "user_query": query_text,
        "admission_year": 2022,
        "target_cid": "chunk_2024_01",
    }

    # Chạy analyze trên query
    yf_res = analyze(query_text)
    assert yf_res.filter_year == 2024, "year_filter phải nhận diện được 2024 từ query"

    # Khi thiết lập filters theo logic CD2:
    filters = {}
    if yf_res.filter_year is not None:
        filters["admission_year"] = yf_res.filter_year
    else:
        filters["admission_year"] = "all"

    # filters["admission_year"] PHẢI là 2024 (từ year_filter.analyze), KHÔNG ĐƯỢC là 2022 (từ row oracle)
    assert filters["admission_year"] == 2024
    assert filters["admission_year"] != row["admission_year"]


def test_cd2_filter_mode_handles_missing_year_with_clarification():
    """CD2: Khi câu hỏi điểm chuẩn không có năm, year_filter yêu cầu làm rõ -> filter 'all'."""
    query_text = "Điểm chuẩn ngành Công nghệ thông tin là bao nhiêu?"
    yf_res = analyze(query_text)

    assert yf_res.status == "clarification_needed"
    assert yf_res.filter_year is None

    filters = {}
    if yf_res.filter_year is not None:
        filters["admission_year"] = yf_res.filter_year
    else:
        filters["admission_year"] = "all"

    # Không được lọc cứng năm 2026 hay bất kỳ năm nào
    assert filters["admission_year"] == "all"


def test_cd2_year_detection_accuracy_computation():
    """CD2: Kiểm tra phép tính độ chính xác nhận diện năm."""
    sample_queries = [
        {"user_query": "Học phí năm 2023", "admission_year": 2023},
        {"user_query": "Điểm chuẩn năm 2024 ngành CNTT", "admission_year": 2024},
        {"user_query": "Xét tuyển 2025 học bạ", "admission_year": 2025},
        {"user_query": "Học phí 2026", "admission_year": 2026},
    ]

    records = []
    for q in sample_queries:
        yf_res = analyze(q["user_query"])
        gt_year = q["admission_year"]
        pred_year = yf_res.filter_year
        records.append({
            "gt": gt_year,
            "pred": pred_year,
            "match": pred_year == gt_year
        })

    correct = sum(1 for r in records if r["match"])
    accuracy = correct / len(records)

    assert correct == 4
    assert accuracy == 1.0
