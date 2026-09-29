import pytest
from app.services.year_filter import analyze, FilterResult

def test_year_filter_valid_years():
    """Kiểm tra các năm hợp lệ trong khoảng [2022, 2026]."""
    for y in [2022, 2023, 2024, 2025, 2026]:
        res = analyze(f"Học phí năm {y} của trường là bao nhiêu?")
        assert res.status == "proceed"
        assert res.filter_year == y

def test_year_filter_unavailable_years_fallback_to_2026():
    """Năm ngoài corpus vẫn trong phạm vi: dùng dữ liệu 2026 và cảnh báo."""
    for y in [2021, 2020, 2019, 2027, 2028, 2030]:
        res = analyze(f"Học phí năm {y} của trường là bao nhiêu?")
        assert res.status == "proceed"
        assert res.code is None
        assert res.filter_year == 2026
        assert res.warning is not None
        assert str(y) in res.warning
        assert "2026" in res.warning

def test_year_filter_in_range_year_uses_exact_year_without_warning():
    """Năm có dữ liệu trong [2022, 2026] phải dùng đúng năm và trả lời trực tiếp."""
    res = analyze("Điểm chuẩn ngành Công nghệ thông tin năm 2026 là bao nhiêu?")
    assert res.status == "proceed"
    assert res.filter_year == 2026
    assert res.warning is None

def test_year_filter_multi_year():
    """Hỏi so sánh nhiều năm -> status clarification_needed và cung cấp danh sách năm."""
    res = analyze("So sánh điểm chuẩn năm 2024 và 2025 ngành logistics")
    assert res.status == "clarification_needed"
    assert res.code == "YEAR_CLARIFICATION_REQUIRED"
    assert len(res.options) > 0
