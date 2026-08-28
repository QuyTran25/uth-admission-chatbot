import sys
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).parent.parent))

from app.services.oos_filter import check_oos

def run_tests():
    test_cases = [
        # --- IN-SCOPE (Should NOT be flagged as OOS) ---
        {
            "query": "Hồi 2023 thì Logistics hệ Chất lượng cao lấy mấy điểm ạ?",
            "expected_oos": False,
            "desc": "ID 20: Logistics chất lượng cao (Không match nhầm lương chất lượng)"
        },
        {
            "query": "Năm 2022 điểm chuẩn ngành Logistics chất lượng cao lấy bao nhiêu điểm?",
            "expected_oos": False,
            "desc": "ID 426: Điểm chuẩn logistics chất lượng cao (Không match nhầm lương)"
        },
        {
            "query": "Điểm chuẩn xét học bạ ngành Logistics chất lượng cao năm 2022 thấp hơn hệ đại trà?",
            "expected_oos": False,
            "desc": "ID 427: Logistics chất lượng cao học bạ"
        },
        {
            "query": "Em định nộp Thạc sĩ Quản lý xây dựng, tỷ lệ chọi năm nay có gắt không?",
            "expected_oos": False,
            "desc": "ID 296: Tỷ lệ chọi hệ Thạc sĩ (Được coi là in-scope)"
        },
        {
            "query": "Cho mình xin số tài khoản ngân hàng để đóng lệ phí thi Tiến sĩ 2025.",
            "expected_oos": False,
            "desc": "ID 368: Số tài khoản đóng lệ phí thi Tiến sĩ (In-scope)"
        },
        {
            "query": "Cần bao nhiêu điểm để đậu Kỹ thuật tàu thủy?",
            "expected_oos": False,
            "desc": "ID 289: Cần bao nhiêu điểm để đậu (In-scope ở dev set)"
        },
        {
            "query": "Cần khoảng bao nhiêu điểm để đỗ ngành Logistics năm 2026?",
            "expected_oos": False,
            "desc": "ID 386: Cần khoảng bao nhiêu điểm để đỗ (In-scope ở dev set)"
        },
        {
            "query": "Trường có xét lý lịch học sinh khi nộp hồ sơ xét tuyển đại học không?",
            "expected_oos": False,
            "desc": "ID 153: Lý lịch học sinh khi nộp hồ sơ xét tuyển (In-scope)"
        },
        {
            "query": "Phòng tuyển sinh E.002 ở cơ sở chính có số điện thoại bàn không ad?",
            "expected_oos": False,
            "desc": "ID 139: Số điện thoại phòng tuyển sinh (In-scope)"
        },
        
        # --- OUT-OF-SCOPE (Should be flagged as OOS) ---
        {
            "query": "Mức lương trung bình của ngành Logistics sau khi ra trường là bao nhiêu?",
            "expected_oos": True,
            "expected_cats": ["luong_thu_nhap"],
            "desc": "Hỏi mức lương sau khi ra trường"
        },
        {
            "query": "Cho em hỏi học phí trường HUTECH có đắt không ạ?",
            "expected_oos": True,
            "expected_cats": ["so_sanh_hoac_hoi_truong_khac"],
            "desc": "Hỏi thông tin trường khác (HUTECH)"
        },
        {
            "query": "Thầy Hiệu trưởng có khó tính không ad?",
            "expected_oos": True,
            "expected_cats": ["danh_gia_nhan_xet_ca_nhan"],
            "desc": "Đánh giá nhận xét cá nhân (Thầy Hiệu trưởng)"
        },
        {
            "query": "Review ký túc xá UTH có sạch sẽ mát mẻ không?",
            "expected_oos": True,
            "expected_cats": ["danh_gia_nhan_xet_ca_nhan"],
            "desc": "Review ký túc xá (Đánh giá cá nhân)"
        },
        {
            "query": "Tra cứu giúp em số báo danh 123456 điểm thi thế nào?",
            "expected_oos": True,
            "expected_cats": ["thong_tin_ca_nhan_bao_mat"],
            "desc": "Tra cứu điểm thi qua SBD người khác"
        },
        {
            "query": "Ad có dự đoán gì về học phí UTH có tăng gấp đôi năm 2027 không?",
            "expected_oos": True,
            "expected_cats": ["nam_tuong_lai"],
            "desc": "Dự đoán năm tương lai xa 2027"
        }
    ]

    failed = 0
    passed = 0
    print("=" * 80)
    print("CHẠY KIỂM THỬ OOS FILTER (HƯỚNG C)")
    print("=" * 80)
    
    for tc in test_cases:
        is_oos, matched = check_oos(tc["query"])
        
        ok = True
        if is_oos != tc["expected_oos"]:
            ok = False
        elif tc["expected_oos"] and "expected_cats" in tc:
            for cat in tc["expected_cats"]:
                if cat not in matched:
                    ok = False
                    
        status_str = "SUCCESS" if ok else "FAILED"
        if ok:
            passed += 1
            print(f"[✓] {tc['desc']}")
            print(f"    Query: {tc['query']}")
            print(f"    OOS? {is_oos} | Matched: {matched}")
        else:
            failed += 1
            print(f"[X] {tc['desc']}")
            print(f"    Query: {tc['query']}")
            print(f"    Expected OOS: {tc['expected_oos']} | Actual: {is_oos}")
            print(f"    Actual Matched: {matched}")
        print("-" * 80)
        
    print(f"\nKẾT QUẢ: Passed {passed}/{passed+failed} tests. Failed {failed} tests.")
    if failed > 0:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    run_tests()
