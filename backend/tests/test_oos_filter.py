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
    ]
    for q in queries:
        is_oos, cats = check_oos(q)
        assert is_oos is False, f"Bị chặn nhầm câu hỏi hợp lệ: '{q}', categories: {cats}"
