"""
gate_budget_grid_search.py — Grid search Gate threshold trên tập RESIDUAL
(sau Union 1+2) với ràng buộc: tổng FPR hệ thống ≤ 10%.

Tìm ngưỡng Gate tối ưu sao cho:
- Union(1+2+Gate) FPR ≤ 10% (ngân sách còn lại ≈ 8% vì 1+2 đã dùng 2.01%)
- Maximize Recall thêm được từ Gate

Nếu KHÔNG tìm được ngưỡng nào thỏa mãn → Gate không thể dùng trong production.
"""

import sys
import json
import pandas as pd
import numpy as np
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from app.services.year_filter import analyze as year_filter_analyze
from app.core.index_store import index_store
from app.services.retrieval_service import retrieve_with_dynamic_routing

# Load Hướng C patterns (đã sửa FP) từ pipeline_union_eval.py
import re
import unicodedata

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

PATTERNS = {
    'du_doan_diem_chuan': [
        r'\bdu doan\b.*\bdiem\b', r'\bdu bao\b.*\bdiem\b',
        r'\bdu kien\b.*\bdiem\b', r'\bdiem\b.*\bdu doan\b',
        r'\bdiem\b.*\bdu kien\b', r'\bdiem\b.*\bdu bao\b',
        r'\bdiem\b.*(tang|giam).*(se|du bao|nam nay)',
        # Giới hạn "can bao nhieu diem de do" vì dev label in-scope
    ],
    'tu_van_chon_nganh_khoi': [
        r'\bnen chon\b.*(nganh|khoi)', r'\bnen hoc\b.*(nganh|truong)',
        r'\bphu hop\b.*(tinh cach|so thich|nang luc)',
        r'\bkhuyen\b.*(em|minh|ban).*(nganh|khoi)',
        r'\btu van\b.*(chon nganh|dinh huong)', r'\bchon nganh\b',
        r'\bdinh huong\b.*(nganh|nghe)', r'\bkhoi nao\b.*(de|tot hon)',
        r'\bnganh nao\b.*(de|phu hop|tot hon)',
        r'\bnen dang ky\b.*(nganh|khoi)', r'\bdang phan van\b.*nganh',
    ],
    'luong_thu_nhap': [
        # FIX: bỏ \bluong\b standalone (match "lượng"), chỉ giữ cụm từ rõ ràng
        r'\bmuc luong\b', r'\bluong sau\b', r'\bluong ra truong\b',
        r'\bthu nhap\b.*(bao nhieu|trung binh|toi thieu|cao nghe nghiep)',
        r'\bra truong\b.*\bluong\b', r'\bsau.*nam\b.*\bluong\b',
        r'\bluong\b.*(ky su|cu nhan)',
    ],
    'co_hoi_viec_lam': [
        r'\bde xin viec\b', r'\bkho xin viec\b', r'\bco hoi viec lam\b',
        r'\btrien vong viec lam\b', r'\btrien vong nghe nghiep\b',
        r'\bviec lam sau tot nghiep\b', r'\bdi lam\b.*(trai nganh|ngoai nganh)',
    ],
    'so_sanh_hoac_hoi_truong_khac': [
        r'\bso sanh\b.*(truong|dai hoc)', r'\bso voi truong\b',
        r'\btruong nao\b.*(day tot|tot hon|nhieu nganh)', r'\bnhieu truong\b',
        r'\bhoc phi truong khac\b', r'\bthong tin truong khac\b',
    ] + OTHER_SCHOOLS,
    'ty_le_choi': [
        r'\bty le choi\b', r'\bty le do\b',
        # Exception: "thac si" không flag
    ],
    'thong_tin_ca_nhan_bao_mat': [
        r'\bso tai khoan\b.*(ca nhan|cua\s*(?:toi|em|ban|minh))',
        r'\bso the ngan hang\b',
        r'\bso dien thoai\b.*(ca nhan|di dong).*(giang vien|thay|co)',
        r'\bsdt cua\b.*(giang vien|thay|co|ong|ba|truong phong)',
        r'\bzalo cua\b.*(giang vien|thay|co|khoa)',
        r'\bdanh sach\b.*(giang vien|thi sinh|cham thi|noi bo)',
        r'\btra cuu\b.*\bdiem\b.*(ban|nguoi|so bao danh)',
        r'\bly lich\b.*(ca nhan)', r'\bdiem ren luyen\b',
    ],
    'thong_tin_chua_cong_bo': [
        r'\bda co bao nhieu\b.*(nop ho so|dang ky)',
        r'\bco ai trung tuyen\b', r'\bthong ke\b.*(ho so|gioi tinh)',
        r'\bbao nhieu nguoi\b.*(nop|dang ky).*(dot|thang)',
    ],
    'xin_tai_lieu_noi_bo': [
        r'\bxin\b.*(tai lieu|file|de thi).*(noi bo|on thi)',
        r'\bbo de thi\b', r'\bgui.*file\b.*(tai lieu)',
        r'\bcho\b.*(file|tai lieu).*(noi bo|cac nam truoc|truong)',
    ],
    'danh_gia_nhan_xet_ca_nhan': [
        r'\bnhan xet\b.*(truong|nganh|de thi|giang vien)',
        r'\breview\b.*(truong|nganh)', r'\bdanh gia\b.*(de thi|gia tri|giang vien|chat luong truong)',
        r'\bco kho tinh\b', r'\bxuong cap\b', r'\bde thi.*kho\b.*nam nay',
        r'\bhien trang\b.*(co so vat chat|truong)',
    ],
    'tu_van_ca_nhan_suc_khoe_tinh_cach': [
        r'\bem la nguoi\b.*(huong noi|ngoai huong|nhat)',
        r'\bcay say song\b', r'\bsay song\b.*(lam|nganh)',
        r'\bco so code\b', r'\bnhat\b.*(chon nganh|hoc nganh)',
    ],
    'cam_ket_dam_bao': [
        r'\bdam bao\b.*(100%|viec lam|xin duoc)',
        r'\bchac suat\b.*(vao lam|xin viec)',
        r'\bcam ket\b.*(viec lam|tuyen dung|xin duoc)',
    ],
    'du_doan_tuong_lai_nganh': [
        r'\btuong lai.*nganh\b', r'\bnganh.*hot\b',
        r'\b\d+\s*nam toi\b.*nganh', r'\bnganh.*xu huong\b',
    ],
    'chuyen_truong': [
        r'\bchuyen truong\b', r'\bduoc chuyen\b.*(qua|sang).*(uth|truong)',
    ],
    'hoi_truong_khac_same_city': [
        r'\bngoai\b.*(uth|truong minh|truong nay).*(truong nao|co truong)',
        r'\bcac truong\b.*day.*nganh',
    ],
    'du_doan_diem_san': [
        r'\bdiem san\b.*(nam nay|2026|bao nhieu)', r'\blay diem san\b',
    ],
    'nam_tuong_lai': [
        r'\bnam\s*202[7-9]\b', r'\bnam\s*20[3-9]\d\b',
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

def main():
    # Load index
    print("Nạp index...")
    index_store.load()
    print("Xong.\n")

    # Load dev set
    df = pd.read_csv(r"d:\uth-admission-chatbot\backend\data\test\dev_questions.csv")
    print(f"Dev set: {len(df)} câu")
    print(f"Phân bố: {df['expected_behavior'].value_counts().to_dict()}")

    refuse_mask = df['expected_behavior'] == 'refuse'
    in_scope_mask = df['expected_behavior'].isin(['answer', 'fallback_warning'])

    # 1. Tính flag Lớp 1 và Lớp 2 cho tất cả câu
    print("\n--- Tính Lớp 1 (year_filter) + Lớp 2 (Hướng C) ---")
    flags_yf = []
    flags_oc = []
    scores = []

    for _, row in df.iterrows():
        query = row['user_query']
        
        # Lớp 1: year_filter
        yr = year_filter_analyze(query)
        flags_yf.append(yr.status == "refused")
        
        # Lớp 2: Hướng C
        flags_oc.append(len(match_oos(query)) > 0)

    df['flagged_yf'] = flags_yf
    df['flagged_oc'] = flags_oc
    df['caught_12'] = df['flagged_yf'] | df['flagged_oc']

    # Metric Union 1+2
    r12 = (refuse_mask & df['caught_12']).sum() / refuse_mask.sum()
    fpr12 = (in_scope_mask & df['caught_12']).sum() / in_scope_mask.sum()
    print(f"Union 1+2: Recall={r12*100:.2f}%, FPR={fpr12*100:.2f}%")

    # 2. Lấy tập residual (refuse chưa bắt được bởi 1+2)
    residual_refuse = df[refuse_mask & ~df['caught_12']].copy()
    residual_in_scope = df[in_scope_mask & ~df['caught_12']].copy()
    print(f"\nResidual: {len(residual_refuse)} refuse + {len(residual_in_scope)} in-scope")

    # 3. Chạy retrieval cho residual in-scope để lấy score_raw
    print("\n--- Chạy retrieval cho residual in-scope (lấy score để tính FPR Gate) ---")
    def get_top1_score(query, filter_year):
        try:
            chunks, _ = retrieve_with_dynamic_routing(query, filter_year=filter_year)
            if chunks:
                return chunks[0].score_raw if chunks[0].score_raw is not None else chunks[0].score
            return 0.0
        except Exception as e:
            print(f"  Error: {e}")
            return None

    # Chạy batch
    residual_in_scope_scores = []
    for _, row in residual_in_scope.iterrows():
        yr = year_filter_analyze(row['user_query'])
        s = get_top1_score(row['user_query'], yr.filter_year)
        residual_in_scope_scores.append(s)
    
    residual_in_scope['gate_score'] = residual_in_scope_scores
    residual_in_scope = residual_in_scope.dropna(subset=['gate_score'])
    print(f"  Đã lấy score cho {len(residual_in_scope)}/{len(residual_in_scope_scores)} câu in-scope residual")

    # 4. Chạy retrieval cho residual refuse để lấy score_raw
    print("\n--- Chạy retrieval cho residual refuse (lấy score để tính Recall Gate) ---")
    residual_refuse_scores = []
    for _, row in residual_refuse.iterrows():
        yr = year_filter_analyze(row['user_query'])
        s = get_top1_score(row['user_query'], yr.filter_year)
        residual_refuse_scores.append(s)
    
    residual_refuse['gate_score'] = residual_refuse_scores
    residual_refuse = residual_refuse.dropna(subset=['gate_score'])
    print(f"  Đã lấy score cho {len(residual_refuse)}/{len(residual_refuse_scores)} câu refuse residual")

    # 5. Grid search ngưỡng trên tập residual
    thresholds = np.arange(0.50, 0.80, 0.01)
    budget_fpr = 0.08  # 8% FPR budget còn lại (10% - 2.01%)

    print(f"\n{'='*70}")
    print(f"GRID SEARCH GATE TRÊN RESIDUAL (FPR budget = {budget_fpr*100:.1f}%)")
    print(f"{'='*70}")
    print(f"{'Threshold':>10} | {'Add Recall':>10} | {'Gate FPR':>9} | {'Total FPR':>9} | {'Total Recall':>11} | {'OK?':>4}")
    print(f"{'-'*70}")

    feasible = []
    base_recall_12 = (refuse_mask & df['caught_12']).sum()
    base_fp_12 = (in_scope_mask & df['caught_12']).sum()
    n_refuse = refuse_mask.sum()
    n_in_scope = in_scope_mask.sum()

    for th in thresholds:
        # Gate bắt thêm những câu residual có score < th
        gate_catch_refuse = (residual_refuse['gate_score'] < th).sum()
        gate_fp_in_scope = (residual_in_scope['gate_score'] < th).sum()
        
        total_recall = (base_recall_12 + gate_catch_refuse) / n_refuse
        total_fpr = (base_fp_12 + gate_fp_in_scope) / n_in_scope
        
        add_recall = gate_catch_refuse / n_refuse
        gate_fpr_alone = gate_fp_in_scope / len(residual_in_scope) if len(residual_in_scope) > 0 else 0
        
        ok = "✓" if total_fpr <= budget_fpr else "✗"
        if total_fpr <= budget_fpr:
            feasible.append((th, total_recall, total_fpr, add_recall, gate_fpr_alone))
        
        print(f"{th:>10.2f} | {add_recall*100:>9.2f}% | {gate_fpr_alone*100:>8.2f}% | {total_fpr*100:>8.2f}% | {total_recall*100:>10.2f}% | {ok:>4}")

    print(f"\n{'='*70}")
    if feasible:
        # Chọn ngưỡng có Recall cao nhất trong những ngưỡng feasible
        best = max(feasible, key=lambda x: x[1])
        print(f"✅ TÌM THẤY NGƯỢNG KHẢ THI:")
        print(f"   Threshold = {best[0]:.2f}")
        print(f"   Tổng Recall = {best[1]*100:.2f}%")
        print(f"   Tổng FPR   = {best[2]*100:.2f}%")
        print(f"   Gate thêm Recall = {best[3]*100:.2f}%")
        print(f"   Gate FPR riêng  = {best[4]*100:.2f}%")
    else:
        print(f"❌ KHÔNG CÓ NGƯỢNG NÀO THỎA MÃN FPR ≤ {budget_fpr*100:.1f}%")
        print(f"   → Gate score-based KHÔNG THỂ DÙNG trong pipeline production")
        print(f"   → Nên tắt Gate (threshold=0, luôn proceed) và dồn lực vào Attribution Gate")

    # Lưu kết quả
    result_df = pd.DataFrame({
        'threshold': thresholds,
        'total_recall': [(base_recall_12 + (residual_refuse['gate_score'] < th).sum()) / n_refuse for th in thresholds],
        'total_fpr': [(base_fp_12 + (residual_in_scope['gate_score'] < th).sum()) / n_in_scope for th in thresholds],
        'add_recall': [(residual_refuse['gate_score'] < th).sum() / n_refuse for th in thresholds],
        'gate_fpr': [(residual_in_scope['gate_score'] < th).sum() / len(residual_in_scope) for th in thresholds],
    })
    out_csv = r"d:\uth-admission-chatbot\backend\eval\results\gate_budget_grid_search.csv"
    result_df.to_csv(out_csv, index=False, encoding='utf-8-sig')
    print(f"\nĐã lưu chi tiết → {out_csv}")

    # Thống kê phân bố score residual để hiểu rõ
    print(f"\n--- Phân bố score residual ---")
    print(f"Refuse residual scores: min={residual_refuse['gate_score'].min():.4f}, "
          f"P25={residual_refuse['gate_score'].quantile(0.25):.4f}, "
          f"median={residual_refuse['gate_score'].median():.4f}, "
          f"P75={residual_refuse['gate_score'].quantile(0.75):.4f}, "
          f"max={residual_refuse['gate_score'].max():.4f}")
    print(f"In-scope residual scores: min={residual_in_scope['gate_score'].min():.4f}, "
          f"P25={residual_in_scope['gate_score'].quantile(0.25):.4f}, "
          f"median={residual_in_scope['gate_score'].median():.4f}, "
          f"P75={residual_in_scope['gate_score'].quantile(0.75):.4f}, "
          f"max={residual_in_scope['gate_score'].max():.4f}")

if __name__ == "__main__":
    main()
