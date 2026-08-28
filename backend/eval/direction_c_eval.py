"""
direction_c_eval.py — Đánh giá Hướng C: Bộ lọc OOS Intent/Keyword trước retrieval.

Chạy toàn bộ 486 câu test_questions.csv, đo Recall/FPR riêng của Hướng C,
sau đó đo Recall/FPR kết hợp (year_filter + Hướng C + Retrieval Gate) so với
chỉ dùng (year_filter + Retrieval Gate).

Không cần Gemini API — hoàn toàn offline.
"""

import sys
import re
import unicodedata
import pandas as pd
from pathlib import Path

DATA_CSV = r"d:\uth-admission-chatbot\backend\data\test\test_questions.csv"
OUT_CSV  = r"d:\uth-admission-chatbot\backend\eval\results\direction_c_eval.csv"

# ---------------------------------------------------------------------------
# 1. Normalize helper
# ---------------------------------------------------------------------------

def normalize(s: str) -> str:
    """Lowercase + bỏ dấu tiếng Việt, giữ 'đ' → 'd' trước khi NFD."""
    s = str(s).lower()
    # 'đ'/'Đ' không tách được bằng NFD vì không phải ký tự tổ hợp
    s = s.replace('đ', 'd').replace('Đ', 'd')
    s = unicodedata.normalize('NFD', s)
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return s


# ---------------------------------------------------------------------------
# 2. Pattern definitions — 13 nhóm OOS intent
# ---------------------------------------------------------------------------

OTHER_SCHOOLS = [
    'hutech', 'bach khoa', 'ton duc thang', 'utc2', r'\butc\b',
    'ueh', 'dh luat', 'su pham ky thuat', 'hang hai viet nam',
    'kinh te tphcm', 'dai hoc luat', 'giao thong van tai ha noi',
    'ngoai bac', 'dh kinh te', 'rmit', 'greenwich', 'fpt',
    'huflit', 'huaf', 'hcmue', 'hcmus', 'hcmut',
]

PATTERNS: dict[str, list[str]] = {
    'du_doan_diem_chuan': [
        r'\bdu doan\b.*\bdiem\b', r'\bdu bao\b.*\bdiem\b',
        r'\bdu kien\b.*\bdiem\b', r'\bdiem\b.*\bdu doan\b',
        r'\bdiem\b.*\bdu kien\b', r'\bdiem\b.*\bdu bao\b',
        r'\bdiem\b.*(tang|giam).*(khong|se|du)',
        r'diem san.*du bao', r'du bao.*diem san',
        r'du doan.*diem san', r'diem san.*du doan',
        r'du doan.*pho diem', r'nam nay.*diem.*cao hon',
        r'diem.*nam nay.*bao nhieu',   # câu hỏi dự đoán tương lai
    ],
    'tu_van_chon_nganh_khoi': [
        r'\bnen chon\b', r'\bnen hoc\b', r'\bnen dang ky\b',
        r'\bnen thi\b.*khoi', r'\bphu hop\b.*(hon|nhat)',
        r'\bde dau hon\b', r'\bkhuyen\b.*(em|minh|ban)',
        r'\btu van\b.*(chon|khoi|nganh|dinh huong)',
        r'\bnen dung khoi\b', r'\bdang phan van\b',
        r'\bchon nganh\b', r'\bkhoi nao.*de\b',
        r'\bnganh nao.*de\b', r'\bdinh huong\b',
    ],
    'luong_thu_nhap': [
        r'\bluong\b.*(co cao|khoi diem|bao nhieu|thang|nam|trung binh|ra truong)',
        r'\bthu nhap\b.*(bao nhieu|trung binh|toi thieu|cao)',
        r'\bluong\b.*(trieu|do|usd)',
        r'\bra truong\b.*\bluong\b', r'\bsau.*nam\b.*\bluong\b',
        r'\bluong\b.*(ky su|cu nhan|nganh)',
        r'\bkiern\b.*bao nhieu',   # "kiếm được bao nhiêu"
    ],
    'co_hoi_viec_lam': [
        r'\bde xin viec\b', r'\bco hoi viec lam\b',
        r'\bdam bao viec lam\b', r'\bgioi thieu viec lam\b',
        r'\bchac suat\b.*(vao lam|nhan|xin duoc)',
        r'\bdam bao\b.*\b100%\b', r'\bxin viec\b',
        r'\bdi lam\b.*(trai nganh|ngoai nganh)',
        r'\bviec lam\b.*(sau|ra truong|dam bao)',
        r'\btiep nhan\b.*(ra truong|sinh vien)',
        r'\bthi truong.*lao dong\b', r'\bnhu cau.*nhan luc\b',
    ],
    'so_sanh_hoac_hoi_truong_khac': [
        r'\bso sanh\b', r'\bso voi truong\b',
        r'\bhon\b.*\btruong\b', r'\btruong nao\b.*(day|tot|nhanh)',
        r'\bnhieu truong\b', r'\btruong khac\b',
        r'\btruong ban\b.*(co|co he|co nganh)',
    ] + OTHER_SCHOOLS,
    'ty_le_choi': [
        r'\bty le choi\b', r'\bty le do\b',
        r'\bty le trung tuyen\b', r'\bkha nang\b.*(dau|trung|do)',
        r'\bthi truot\b', r'\bbao nhieu nguoi\b.*\bdang ky\b',
    ],
    'thong_tin_ca_nhan_bao_mat': [
        r'\bso dien thoai\b', r'\bzalo\b',
        r'\bso tai khoan\b', r'\bso the ngan hang\b',
        r'\bdanh sach\b.*(thi sinh|giang vien|cham thi)',
        r'\btra cuu\b.*\bdiem\b.*(ban|nguoi|so bao danh)',
        r'\bthong tin ca nhan\b', r'\bly lich\b',
        r'\bdiem ren luyen\b', r'\bsdt cua\b',
    ],
    'thong_tin_chua_cong_bo': [
        r'\bda co bao nhieu\b.*\bnop ho so\b',
        r'\bco ai trung tuyen\b',
        r'\bthong ke\b.*(ho so|gioi tinh)',
        r'\bbao nhieu nguoi\b.*(nop|dang ky|trung tuyen)',
    ],
    'xin_tai_lieu_noi_bo': [
        r'\bxin\b.*(tai lieu|file|de thi).*(noi bo|on thi)',
        r'\bbo de thi\b', r'\bgui file\b',
        r'\bcho\b.*(tai lieu|file)',
    ],
    'danh_gia_nhan_xet_ca_nhan': [
        r'\bnhan xet\b.*(giup|ve)', r'\breview\b',
        r'\bdanh gia\b.*(de thi|hoc tap|gia tri|cua truong|giang vien)',
        r'\bco kho tinh\b', r'\bdu doan.*de.*kho\b',
        r'\bgia tri\b.*(nhu chinh quy|bang cap)', r'\bxuong cap\b',
        r'\bhien trang\b.*co so vat chat',
    ],
    'tu_van_ca_nhan_suc_khoe_tinh_cach': [
        r'\bem la nguoi\b', r'\bhuong noi\b', r'\bso\b.*\bviec\b',
        r'\bsuc khoe.*yeu\b', r'\bcay say song\b',
        r'\bco so code\b', r'\bgioi ve\b',
    ],
    'cam_ket_dam_bao': [
        r'\bcam ket\b', r'\bdam bao\b.*\b100%\b', r'\bchac suat\b',
    ],
    'du_doan_tuong_lai_nganh': [
        r'\btuong lai.*nganh\b', r'\bnganh.*hot\b',
        r'\b\d+\s*nam toi\b', r'\bphat trien.*nganh\b',
        r'\bnganh.*xu huong\b',
    ],
}


def match_oos(query: str) -> list[str]:
    """Trả về danh sách nhóm OOS match được, rỗng nếu không match."""
    q = normalize(query)
    matched = []
    for label, pats in PATTERNS.items():
        for p in pats:
            if re.search(p, q):
                matched.append(label)
                break
    return matched


# ---------------------------------------------------------------------------
# 3. Chạy đánh giá
# ---------------------------------------------------------------------------

def main():
    df = pd.read_csv(DATA_CSV)
    print(f"Tổng câu hỏi: {len(df)}")
    print(f"Phân bố nhãn:\n{df['expected_behavior'].value_counts().to_string()}\n")

    df['oos_matched'] = df['user_query'].apply(match_oos)
    df['direction_c_flagged'] = df['oos_matched'].apply(lambda x: len(x) > 0)

    # -----------------------------------------------------------------------
    # Metric Hướng C đơn lẻ
    # -----------------------------------------------------------------------
    refuse_mask    = df['expected_behavior'] == 'refuse'
    answer_mask    = df['expected_behavior'] == 'answer'
    fallback_mask  = df['expected_behavior'] == 'fallback_warning'
    in_scope_mask  = answer_mask | fallback_mask

    n_refuse   = refuse_mask.sum()
    n_answer   = answer_mask.sum()
    n_fallback = fallback_mask.sum()
    n_in_scope = in_scope_mask.sum()

    c_caught  = (refuse_mask & df['direction_c_flagged']).sum()
    c_fp_ans  = (answer_mask & df['direction_c_flagged']).sum()
    c_fp_fall = (fallback_mask & df['direction_c_flagged']).sum()
    c_fp_all  = (in_scope_mask & df['direction_c_flagged']).sum()

    recall_c = c_caught / n_refuse if n_refuse > 0 else 0
    fpr_c    = c_fp_all / n_in_scope if n_in_scope > 0 else 0

    print("=" * 60)
    print("HƯỚNG C — OOS Intent Pre-filter")
    print("=" * 60)
    print(f"Recall  (refuse bắt được): {c_caught}/{n_refuse} = {recall_c*100:.1f}%")
    print(f"FPR     (in-scope chặn nhầm): {c_fp_all}/{n_in_scope} = {fpr_c*100:.2f}%")
    print(f"  └─ Answer chặn nhầm:   {c_fp_ans}/{n_answer} ({c_fp_ans/n_answer*100:.2f}%)")
    print(f"  └─ Fallback chặn nhầm: {c_fp_fall}/{n_fallback} ({c_fp_fall/n_fallback*100:.2f}%)")

    # Breakdown theo nhóm OOS
    print("\n--- Breakdown Recall theo nhóm OOS ---")
    for label in PATTERNS:
        caught = refuse_mask & df['oos_matched'].apply(lambda x: label in x)
        fp     = in_scope_mask & df['oos_matched'].apply(lambda x: label in x)
        print(f"  {label:45s}: recall={caught.sum():3d}/{n_refuse}  FP={fp.sum():3d}")

    # -----------------------------------------------------------------------
    # False Positives — câu in-scope bị chặn nhầm
    # -----------------------------------------------------------------------
    fp_rows = df[in_scope_mask & df['direction_c_flagged']]
    print(f"\n=== FP chi tiết: {len(fp_rows)} câu in-scope bị chặn nhầm ===")
    for _, r in fp_rows.iterrows():
        print(f"  ID={r['id']}  [{r['expected_behavior']}]  matched={r['oos_matched']}")
        print(f"    Query: {r['user_query'][:80]}")

    # -----------------------------------------------------------------------
    # Missed refuse — câu refuse không bị bắt bởi Hướng C
    # -----------------------------------------------------------------------
    missed = df[refuse_mask & ~df['direction_c_flagged']]
    print(f"\n=== Missed refuse ({len(missed)} câu) ===")
    for _, r in missed.iterrows():
        print(f"  ID={r['id']}  cat={r['category']}  intent={r['intent']}")
        print(f"    Query: {r['user_query'][:80]}")

    # -----------------------------------------------------------------------
    # Lưu kết quả
    # -----------------------------------------------------------------------
    df.to_csv(OUT_CSV, index=False, encoding='utf-8-sig')
    print(f"\nLưu kết quả → {OUT_CSV}")
    print("HOÀN TẤT HƯỚNG C EVAL.")


if __name__ == "__main__":
    main()
