import pytest
from app.services.year_filter import analyze, FilterResult

def test_year_filter_valid_years():
    """Kiểm tra các năm hợp lệ trong khoảng [2022, 2026]."""
    for y in [2022, 2023, 2024, 2025, 2026]:
        res = analyze(f"Học phí năm {y} của trường là bao nhiêu?")
        assert res.status == "proceed"
        assert res.filter_year == y

def test_year_filter_valid_years():
    """Kiểm tra các năm hợp lệ trong khoảng [2022, 2026]."""
    for y in [2022, 2023, 2024, 2025, 2026]:
        res = analyze(f"Học phí năm {y} của trường là bao nhiêu?")
        assert res.status == "proceed"
        assert res.filter_year == y


def test_year_filter_unsupported_years_refused():
    """CD8: Năm ngoài khoảng [2022, 2026] phải bị từ chối rõ ràng, không fallback lùi về 2026."""
    for y in [2021, 2020, 2019, 2027, 2028, 2030]:
        res = analyze(f"Học phí năm {y} của trường là bao nhiêu?")
        assert res.status == "refused"
        assert res.code == "YEAR_NOT_SUPPORTED"
        assert res.filter_year == y
        assert res.refusal_source == "year_not_supported"


def test_year_filter_in_range_year_uses_exact_year_without_warning():
    """Năm có dữ liệu trong [2022, 2026] phải dùng đúng năm và trả lời trực tiếp."""
    res = analyze("Điểm chuẩn ngành Công nghệ thông tin năm 2026 là bao nhiêu?")
    assert res.status == "proceed"
    assert res.filter_year == 2026
    assert res.warning is None


def test_year_filter_multi_year():
    """CD8: Hỗ trợ nhiều năm ngay cả khi không có từ khóa 'so sánh'."""
    # Có từ so sánh
    res1 = analyze("So sánh điểm chuẩn năm 2024 và 2025 ngành logistics")
    assert res1.status == "clarification_needed"
    assert res1.code == "YEAR_CLARIFICATION_REQUIRED"

    # Không có từ 'so sánh', chỉ liệt kê 2 năm
    res2 = analyze("Điểm chuẩn ngành Logistics năm 2023 và 2024?")
    assert res2.status == "clarification_needed"
    assert res2.code == "YEAR_CLARIFICATION_REQUIRED"
    assert len(res2.options) >= 2


def test_year_filter_missing_year_requests_clarification():
    """CD8: Câu hỏi điểm chuẩn thiếu năm phải hỏi lại người dùng."""
    res = analyze("Điểm chuẩn ngành Công nghệ thông tin là bao nhiêu?")
    assert res.status == "clarification_needed"
    assert res.code == "YEAR_CLARIFICATION_REQUIRED"
    assert len(res.options) == 5
