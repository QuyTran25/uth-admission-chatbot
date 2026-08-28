"""
pipeline_union_eval.py — Đo union thực tế của 3 lớp lọc.

⚠️  PHAM VI: Chi chay tren DEV SET (dev_questions.csv, 390 cau).
TUYET DOI KHONG doc test_questions_locked.csv giua chung.

Moi cau hoi duoc danh dau:
  - flagged_year_filter: year_filter.analyze() tra ve status='refused'
  - flagged_direction_c: OOS intent pattern match (Huong C)
  - flagged_retrieval_gate: score < threshold (offline, khong can Gemini)
  - caught_union: ANY(3 flag tren) = True

Output:
  1. Bang Union Recall / FPR thuc do tren dev set
  2. Danh sach chinh xac cau refuse sot sau 2 lop dau
  3. Phan bo score_raw cua nhom sot

Khong can Gemini API.
"""

import sys
import re
import json
import unicodedata
import pandas as pd
import numpy as np
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from app.services.year_filter import analyze as year_filter_analyze
from app.core.index_store import index_store
from app.services.retrieval_service import retrieve_with_dynamic_routing

# ⚠️ DEV SET ONLY — không đọc locked set
DATA_CSV      = r"d:\uth-admission-chatbot\backend\data\test\dev_questions.csv"
GATE_THRESHOLD = 0.62   # ngưỡng mới (FPR-friendly), hard-code để đo thực tế
OUT_CSV       = r"d:\uth-admission-chatbot\backend\eval\results\pipeline_union_eval_dev.csv"


# ---------------------------------------------------------------------------
# 1. OOS Intent patterns (Hướng C — đã sửa 14 FP)
# ---------------------------------------------------------------------------

def normalize(s: str) -> str:
    s = str(s).lower()
    s = s.replace('đ', 'd').replace('Đ', 'd')
    s = unicodedata.normalize('NFD', s)
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return s


OTHER_SCHOOLS = [
    'hutech', 'bach khoa', 'ton duc thang', 'utc2', r'\butc\b',
    'ueh', r'\bdh luat\b', 'su pham ky thuat', 'hang hai viet nam',
    'kinh te tphcm', 'dai hoc luat', 'giao thong van tai ha noi',
    'ngoai bac', r'\bdh kinh te\b', 'rmit', 'greenwich', r'\bfpt\b',
    'huflit', 'hcmue', 'hcmus', 'hcmut',
]

PATTERNS: dict[str, list[str]] = {
    'du_doan_diem_chuan': [
        r'\bdu doan\b.*\bdiem\b',
        r'\bdu bao\b.*\bdiem\b',
        r'\bdu kien\b.*\bdiem\b',
        r'\bdiem\b.*\bdu doan\b',
        r'\bdiem\b.*\bdu kien\b',
        r'\bdiem\b.*\bdu bao\b',
        r'\bdiem\b.*(tang|giam).*(se|du bao|nam nay)',
        r'\bnam nay\b.*\bdiem\b.*(bao nhieu|la bao)',  # FIX: loại "điểm năm nay là bao nhiêu" là IN-SCOPE
        r'\bdiem san\b.*(du bao|du doan)',
        r'\bdu doan\b.*diem san',
        # Thêm: bao nhiêu điểm để đỗ = dự đoán
        r'\bcao bao nhieu\b.*\bdau\b',
        r'\bcan bao nhieu diem\b.*(dau|do|trung)',
        r'\bkhoang bao nhieu diem\b.*(dau|do|trung)',
    ],
    'tu_van_chon_nganh_khoi': [
        r'\bnen chon\b.*(nganh|khoi)',
        r'\bnen hoc\b.*(nganh|truong)',
        r'\bphu hop\b.*(tinh cach|so thich|nang luc)',  # FIX: không chặn "phù hợp điều kiện"
        r'\bkhuyen\b.*(em|minh|ban).*(nganh|khoi)',
        r'\btu van\b.*(chon nganh|dinh huong)',
        r'\bchon nganh\b', r'\bdinh huong\b.*(nganh|nghe)',
        r'\bkhoi nao\b.*(de|tot hon)',
        r'\bnganh nao\b.*(de|phu hop|tot hon)',
        r'\bnen dang ky\b.*(nganh|khoi)',
        r'\bdang phan van\b.*nganh',
    ],
    'luong_thu_nhap': [
        r'\bluong\b.*(khoi diem|bao nhieu|trieu|do|usd)',
        r'\bthu nhap\b.*(bao nhieu|trung binh|toi thieu|cao nghe nghiep)',
        r'\bra truong\b.*\bluong\b',
        r'\bsau.*nam\b.*\bluong\b',
        r'\bluong\b.*(ky su|cu nhan)',
        # FIX: loại "chất lượng cao" tạo FP (ID=20,426,427)
        # Không dùng lookahead — chỉ match khi "lương" rõ ràng không phải "chất lượng"
    ],
    'co_hoi_viec_lam': [
        r'\bde xin viec\b', r'\bkho xin viec\b',
        r'\bco hoi viec lam\b',
        r'\btrien vong viec lam\b', r'\btrien vong nghe nghiep\b',
        r'\bviec lam sau tot nghiep\b',
        r'\bdi lam\b.*(trai nganh|ngoai nganh)',
        # FIX: bỏ 'nhu cau tuyen dung' — khớp ID=304 (in-scope: thư giới thiệu của Sở)
    ],
    'so_sanh_hoac_hoi_truong_khac': [
        r'\bso sanh\b.*(truong|dai hoc)',
        r'\bso voi truong\b',
        r'\btruong nao\b.*(day tot|tot hon|nhieu nganh)',
        r'\bnhieu truong\b',
        r'\bhoc phi truong khac\b',
        r'\bthong tin truong khac\b',
    ] + OTHER_SCHOOLS,
    'ty_le_choi': [
        r'\bty le choi\b',
        r'\bty le do\b',
        # FIX: loại "tỷ lệ chọi Thạc sĩ" — ID=296 là in-scope (thạc sĩ có chỉ tiêu)
        # → giữ pattern nhưng add exception: nếu câu có "thac si" thì không flag
        # → Thực tế sẽ xử lý qua context, tạm chấp nhận 1 FP này
        r'\bty le trung tuyen\b.*(bao nhieu|nam nay)',
        r'\bbao nhieu nguoi\b.*(nop|dang ky).*nganh',
    ],
    # Thu hẹp thong_tin_ca_nhan_bao_mat:
    # In-scope: SĐT/email phòng ban trường, Zalo OA trường
    # Out-of-scope: SĐT/Zalo cá nhân GV/HS, TKNH, danh sách nội bộ, tra cứu điểm người khác
    'thong_tin_ca_nhan_bao_mat': [
        # FIX: bỏ "số tài khoản" đứng một mình — ID=368 (đóng lệ phí là IN-SCOPE)
        # Chỉ flag TKNH cá nhân, không phải tài khoản trường
        r'\bso tai khoan\b.*(ca nhan|cua\s*(?:toi|em|ban|minh))',
        r'\bso the ngan hang\b',
        r'\bso dien thoai\b.*(ca nhan|di dong).*(giang vien|thay|co)',
        r'\bsdt cua\b.*(giang vien|thay|co|ong|ba|truong phong)',
        r'\bzalo cua\b.*(giang vien|thay|co|khoa)',
        r'\bdanh sach\b.*(giang vien|thi sinh|cham thi|noi bo)',
        r'\btra cuu\b.*\bdiem\b.*(ban|nguoi|so bao danh)',
        # FIX: bỏ 'ly lich hoc sinh' — in-scope khi hỏi hồ sơ xét tuyển (ID=153)
        r'\bly lich\b.*(ca nhan)',
        r'\bdiem ren luyen\b',
    ],
    'thong_tin_chua_cong_bo': [
        r'\bda co bao nhieu\b.*(nop ho so|dang ky)',
        r'\bco ai trung tuyen\b',
        r'\bthong ke\b.*(ho so|gioi tinh)',
        r'\bbao nhieu nguoi\b.*(nop|dang ky).*(dot|thang)',
    ],
    'xin_tai_lieu_noi_bo': [
        r'\bxin\b.*(tai lieu|file|de thi).*(noi bo|on thi)',
        r'\bbo de thi\b',
        r'\bgui.*file\b.*(tai lieu)',
        r'\bcho\b.*(file|tai lieu).*(noi bo|cac nam truoc|truong)',
    ],
    'danh_gia_nhan_xet_ca_nhan': [
        r'\bnhan xet\b.*(truong|nganh|de thi|giang vien)',
        r'\breview\b.*(truong|nganh)',
        r'\bdanh gia\b.*(de thi|gia tri|giang vien|chat luong truong)',
        r'\bco kho tinh\b', r'\bxuong cap\b',
        r'\bde thi.*kho\b.*nam nay',
        r'\bhien trang\b.*(co so vat chat|truong)',
    ],
    'tu_van_ca_nhan_suc_khoe_tinh_cach': [
        r'\bem la nguoi\b.*(huong noi|ngoai huong|nhat)',
        # FIX: bỏ 'suc khoe yeu co duoc hoc' — ID=24 in-scope (hỏi điều kiện sức khỏe)
        r'\bcay say song\b', r'\bsay song\b.*(lam|nganh)',
        r'\bco so code\b',
        r'\bnhat\b.*(chon nganh|hoc nganh)',
    ],
    'cam_ket_dam_bao': [
        # FIX: bỏ 'cam ket' standalone → ID=51 in-scope
        r'\bdam bao\b.*(100%|viec lam|xin duoc)',
        r'\bchac suat\b.*(vao lam|xin viec)',
        r'\bcam ket\b.*(viec lam|tuyen dung|xin duoc)',
    ],
    'du_doan_tuong_lai_nganh': [
        r'\btuong lai.*nganh\b', r'\bnganh.*hot\b',
        r'\b\d+\s*nam toi\b.*nganh', r'\bnganh.*xu huong\b',
    ],
    # Nhóm năm ngoài kho (2000-2021) — CHỈ dùng trên DEV, không nhắm locked
    # FIX: loại bỏ pattern này vì gây FP trên ID=28 (fallback_warning năm 2020)
    # year_filter đã xử lý các câu hỏi năm ngoài phạm vi → không cần Hướng C bắt

    'chuyen_truong': [
        r'\bchuyen truong\b',
        r'\bduoc chuyen\b.*(qua|sang).*(uth|truong)',
    ],

    # Thêm pattern mới cho câu miss trên DEV SET
    'hoi_truong_khac_same_city': [
        r'\bngoai\b.*(uth|truong minh|truong nay).*(truong nao|co truong)',
        r'\bcac truong\b.*day.*nganh',
    ],
    'du_doan_diem_san': [
        r'\bdiem san\b.*(nam nay|2026|bao nhieu)',
        r'\blay diem san\b',
    ],
    'nam_tuong_lai': [
        # Năm tương lai > 2026 (dự đoán chính sách)
        r'\bnam\s*202[7-9]\b',
        r'\bnam\s*20[3-9]\d\b',
    ],
}


def match_oos(query: str) -> list[str]:
    q = normalize(query)
    matched = []
    for label, pats in PATTERNS.items():
        for p in pats:
            if re.search(p, q):
                matched.append(label)
                break
    return matched


# ---------------------------------------------------------------------------
# 2. Main evaluation
# ---------------------------------------------------------------------------

def main():
    # Load index cho Retrieval Gate
    print("Nạp index FAISS + BM25...")
    index_store.load()
    print("Nạp index hoàn tất!\n")

    gate_threshold = GATE_THRESHOLD
    print(f"Gate threshold (FPR-friendly): {gate_threshold}\n")

    df = pd.read_csv(DATA_CSV)
    print(f"⚠️  DEV SET ONLY — Không đọc locked set.")
    print(f"Tổng câu hỏi: {len(df)}")
    print(f"Phân bố nhãn:\n{df['expected_behavior'].value_counts().to_string()}\n")

    results = []
    n = len(df)

    for i, row in df.iterrows():
        if (i+1) % 50 == 0:
            print(f"  Đang xử lý {i+1}/{n}...")

        query    = row['user_query']
        behavior = row['expected_behavior']
        qid      = row['id']

        # --- Lớp 1: year_filter ---
        yr = year_filter_analyze(query)
        flagged_yf = (yr.status == "refused")

        # --- Lớp 2: Hướng C (OOS intent) ---
        oos_matched = match_oos(query)
        flagged_oc  = len(oos_matched) > 0

        # --- Lớp 3: Retrieval Gate (chỉ chạy nếu 2 lớp trên chưa bắt) ---
        top1_score_raw = None
        flagged_gate   = False

        if not flagged_yf and not flagged_oc:
            try:
                chunks, _ = retrieve_with_dynamic_routing(query, filter_year=yr.filter_year)
                if chunks:
                    top1_score_raw = chunks[0].score_raw
                    flagged_gate = (top1_score_raw < gate_threshold)
                else:
                    flagged_gate = True  # không có chunk = từ chối
                    top1_score_raw = 0.0
            except Exception as e:
                print(f"  [WARN] ID={qid}: {e}")
                flagged_gate = False

        caught_union = flagged_yf or flagged_oc or flagged_gate

        results.append({
            "id":               qid,
            "user_query":       query[:80],
            "expected_behavior": behavior,
            "category":         row['category'],
            "intent":           row['intent'],
            "flagged_year_filter": flagged_yf,
            "yf_status":        yr.status,
            "flagged_direction_c": flagged_oc,
            "oos_matched":      str(oos_matched),
            "flagged_gate":     flagged_gate,
            "top1_score_raw":   round(top1_score_raw, 5) if top1_score_raw is not None else None,
            "caught_union":     caught_union,
        })

    out_df = pd.DataFrame(results)
    out_df.to_csv(OUT_CSV, index=False, encoding='utf-8-sig')
    print(f"\nĐã lưu bảng chi tiết → {OUT_CSV}\n")

    # -----------------------------------------------------------------------
    # 3. Tính metric thực tế
    # -----------------------------------------------------------------------
    refuse_mask   = out_df['expected_behavior'] == 'refuse'
    answer_mask   = out_df['expected_behavior'] == 'answer'
    fallback_mask = out_df['expected_behavior'] == 'fallback_warning'
    in_scope_mask = answer_mask | fallback_mask

    n_refuse   = refuse_mask.sum()
    n_in_scope = in_scope_mask.sum()

    def report_layer(name, flag_col, mask_refuse=refuse_mask, mask_in_scope=in_scope_mask):
        caught = (mask_refuse & out_df[flag_col]).sum()
        fp     = (mask_in_scope & out_df[flag_col]).sum()
        recall = caught / n_refuse   if n_refuse   > 0 else 0
        fpr    = fp     / n_in_scope if n_in_scope > 0 else 0
        print(f"  {name:30s}: Recall={caught:3d}/{n_refuse} ({recall*100:5.1f}%)  FPR={fp:3d}/{n_in_scope} ({fpr*100:4.2f}%)")
        return caught, fp

    print("=" * 65)
    print("METRIC THỰC ĐO TỪNG LỚP VÀ UNION")
    print("=" * 65)
    report_layer("Lớp 1 — year_filter",      "flagged_year_filter")
    report_layer("Lớp 2 — Hướng C (intent)", "flagged_direction_c")
    report_layer("Lớp 3 — Retrieval Gate",   "flagged_gate")

    # Union 2 lớp đầu
    out_df['caught_2layer'] = out_df['flagged_year_filter'] | out_df['flagged_direction_c']
    c2 = (refuse_mask & out_df['caught_2layer']).sum()
    fp2 = (in_scope_mask & out_df['caught_2layer']).sum()
    print(f"  {'Union Lớp 1+2':30s}: Recall={c2:3d}/{n_refuse} ({c2/n_refuse*100:5.1f}%)  FPR={fp2:3d}/{n_in_scope} ({fp2/n_in_scope*100:4.2f}%)")

    # Union cả 3 lớp
    cu = (refuse_mask & out_df['caught_union']).sum()
    fpu = (in_scope_mask & out_df['caught_union']).sum()
    print(f"  {'UNION 3 Lớp (thực đo)':30s}: Recall={cu:3d}/{n_refuse} ({cu/n_refuse*100:5.1f}%)  FPR={fpu:3d}/{n_in_scope} ({fpu/n_in_scope*100:4.2f}%)")

    # -----------------------------------------------------------------------
    # 4. Phân tích câu refuse còn sót sau 2 lớp đầu
    # -----------------------------------------------------------------------
    sot_2layer = out_df[refuse_mask & ~out_df['caught_2layer']]
    print(f"\n{'='*65}")
    print(f"CÂU REFUSE SÓT SAU LỚP 1+2: {len(sot_2layer)} câu")
    print(f"{'='*65}")

    # Phân bố score của nhóm sót
    sot_scores = sot_2layer['top1_score_raw'].dropna()
    if len(sot_scores) > 0:
        print(f"Phân bố score_raw nhóm sót (câu cần Gate xử lý):")
        print(f"  Min:    {sot_scores.min():.4f}")
        print(f"  P25:    {sot_scores.quantile(0.25):.4f}")
        print(f"  Median: {sot_scores.median():.4f}")
        print(f"  P75:    {sot_scores.quantile(0.75):.4f}")
        print(f"  Max:    {sot_scores.max():.4f}")
        # Số câu có score < gate_threshold
        gate_catchable = (sot_scores < gate_threshold).sum()
        print(f"\n  Câu có score < {gate_threshold} (Gate bắt được): {gate_catchable}/{len(sot_scores)} ({gate_catchable/len(sot_scores)*100:.1f}%)")
        print(f"  Câu có score >= {gate_threshold} (Gate KHÔNG bắt): {len(sot_scores)-gate_catchable}/{len(sot_scores)} ({(1-gate_catchable/len(sot_scores))*100:.1f}%)")

    print("\nDanh sách câu sót (cần Gate hoặc Attribution Gate xử lý):")
    for _, r in sot_2layer.iterrows():
        score_str = f"score={r['top1_score_raw']:.4f}" if r['top1_score_raw'] is not None else "score=N/A"
        gate_str = "Gate-CAUGHT" if r['flagged_gate'] else "Gate-MISS"
        print(f"  ID={r['id']:3d}  [{gate_str}]  {score_str}  cat={r['category']}")
        print(f"         {r['user_query'][:75]}")

    # -----------------------------------------------------------------------
    # 5. FP còn lại của Hướng C (đã sửa)
    # -----------------------------------------------------------------------
    fp_oc = out_df[in_scope_mask & out_df['flagged_direction_c']]
    print(f"\n{'='*65}")
    print(f"FP HƯỚNG C SAU SỬA (còn lại): {len(fp_oc)} câu")
    print(f"{'='*65}")
    for _, r in fp_oc.iterrows():
        print(f"  ID={r['id']}  [{r['expected_behavior']}]  matched={r['oos_matched']}")
        print(f"    {r['user_query'][:80]}")

    print("\nHOÀN TẤT PIPELINE UNION EVAL.")


if __name__ == "__main__":
    main()
