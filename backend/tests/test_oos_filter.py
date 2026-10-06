import pytest
from app.services.oos_filter import check_oos

def test_oos_prediction_query():
    """Dự đoán điểm chuẩn phải bị coi là OOS."""
    is_oos, cats = check_oos("Dự đoán điểm chuẩn ngành logistics năm nay tăng hay giảm?")
    assert is_oos is True
    assert "du_doan_diem_chuan" in cats

def test_oos_career_advice_query():
    """Tư vấn chọn ngành theo tính cách/sở thích phải bị coi là OOS."""
    is_oos, cats = check_oos("Em thích giao tiếp thì nên chọn ngành nào?")
    assert is_oos is True
    assert "tu_van_chon_nganh_khoi" in cats

def test_oos_salary_query():
    """Hỏi mức lương ra trường phải bị coi là OOS."""
    is_oos, cats = check_oos("Mức lương ra trường của kỹ sư cầu đường là bao nhiêu?")
    assert is_oos is True
    assert "luong_thu_nhap" in cats

def test_oos_compare_other_school():
    """Hỏi so sánh hoặc thông tin trường khác phải bị coi là OOS."""
    is_oos, cats = check_oos("So với trường Bách Khoa thì UTH học phí thế nào?")
    assert is_oos is True
    assert "so_sanh_hoac_hoi_truong_khac" in cats

def test_in_scope_queries_not_blocked():
    """Các câu hỏi tuyển sinh chính thống không được bị chặn nhầm."""
    queries = [
        "Chỉ tiêu tuyển sinh ngành Công nghệ thông tin năm 2026 là bao nhiêu?",
        "Học phí hệ đại học chính quy của trường?",
        "Các phương thức xét tuyển vào trường năm 2026 gồm những gì?",
        "Hồ sơ nhập học gồm những giấy tờ gì?",
        "Trường có những cơ sở đào tạo nào?",
        # CD4: Các câu hỏi dễ bị dính false-positive từ dev set
        "Hồi 2023 thì Logistics hệ Chất lượng cao lấy mấy điểm ạ?",
        "Năm 2022 điểm chuẩn ngành Logistics chất lượng cao lấy bao nhiêu điểm?",
        "Điểm chuẩn ngành kinh tế vận tải năm 2024?",
        "Em muốn hỏi về thủ tục chuyển ngành trong trường UTH?",
        "Cần bao nhiêu điểm để đậu Kỹ thuật tàu thủy?",
    ]
    for q in queries:
        is_oos, cats = check_oos(q)
        assert is_oos is False, f"Bị chặn nhầm câu hỏi hợp lệ: '{q}', categories: {cats}"


def test_oos_does_not_override_year_filter_for_2019():
    """Case năm 2019: Câu hỏi thuần tuyển sinh năm cũ không bị OOS bắt nhầm; nhường cho year_filter."""
    q = "Điểm chuẩn năm 2019 ngành Công nghệ thông tin là bao nhiêu?"
    is_oos, cats = check_oos(q)
    assert is_oos is False, f"OOS không được bắt nhầm câu hỏi năm 2019: {cats}"

    # Khi year_filter báo refused, OOS filter cũng không ghi đè
    is_oos_refused, cats_refused = check_oos(q, year_filter_status="refused")
    assert is_oos_refused is False
