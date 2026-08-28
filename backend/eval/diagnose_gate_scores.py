"""
diagnose_gate_scores.py — Xuất bảng phân bố điểm score_raw theo từng nhóm expected_behavior
để chẩn đoán khả năng tách in-scope vs out-of-scope bằng ngưỡng score.
"""
import sys
import pandas as pd
import numpy as np
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from app.core.index_store import index_store
from app.services.year_filter import analyze
from app.services.retrieval_service import retrieve_with_dynamic_routing

DATA_DIR = r"d:\uth-admission-chatbot\backend\data\test"
DEV_CSV = f"{DATA_DIR}\\dev_questions.csv"

def main():
    print("Nạp index...")
    index_store.load()
    print("Nạp index hoàn tất!\n")

    df = pd.read_csv(DEV_CSV)
    rows = []

    print(f"Đang phân tích điểm score_raw cho {len(df)} câu hỏi...")
    for _, row in df.iterrows():
        query = row['user_query']
        behavior = row['expected_behavior']
        category = row['category']

        yr = analyze(query)
        
        # Đã bị chặn bởi keyword (year_filter)
        if yr.status == "refused":
            rows.append({
                "query": query[:60],
                "expected_behavior": behavior,
                "category": category,
                "blocked_by_keyword": True,
                "top1_score_raw": None,
                "margin": None,
                "n_chunks": 0
            })
            continue

        chunks, _ = retrieve_with_dynamic_routing(query, filter_year=yr.filter_year)
        top1 = chunks[0].score_raw if chunks else None
        margin = (chunks[0].score_raw - chunks[1].score_raw) if len(chunks) >= 2 else top1

        rows.append({
            "query": query[:60],
            "expected_behavior": behavior,
            "category": category,
            "blocked_by_keyword": False,
            "top1_score_raw": round(top1, 6) if top1 is not None else None,
            "margin": round(margin, 6) if margin is not None else None,
            "n_chunks": len(chunks)
        })

    out_df = pd.DataFrame(rows)
    out_path = r"d:\uth-admission-chatbot\backend\eval\results\gate_score_diagnosis.csv"
    out_df.to_csv(out_path, index=False, encoding='utf-8-sig')
    print(f"Đã lưu bảng điểm ra: {out_path}\n")

    # Phân tích theo nhóm
    print("=" * 60)
    print("PHÂN BỐ score_raw THEO NHÓM (chỉ câu lọt qua year_filter)")
    print("=" * 60)
    # Chỉ lấy câu không bị chặn keyword
    active = out_df[~out_df['blocked_by_keyword']]
    
    for grp_name, grp in active.groupby('expected_behavior'):
        scores = grp['top1_score_raw'].dropna()
        print(f"\n[{grp_name}] — {len(grp)} câu (qua year_filter: {len(grp[~grp['top1_score_raw'].isna()])})")
        if len(scores) > 0:
            print(f"  Min:    {scores.min():.4f}")
            print(f"  Median: {scores.median():.4f}")
            print(f"  Mean:   {scores.mean():.4f}")
            print(f"  P25:    {scores.quantile(0.25):.4f}")
            print(f"  P75:    {scores.quantile(0.75):.4f}")
            print(f"  Max:    {scores.max():.4f}")

    print("\n" + "=" * 60)
    print("SỐ LƯỢNG CÂU BỊ CHẶN BỞI KEYWORD vs LỌT QUA GATE (dev set)")
    print("=" * 60)
    refuse_df = out_df[out_df['expected_behavior'] == 'refuse']
    print(f"Tổng câu nhãn 'refuse': {len(refuse_df)}")
    print(f"  Bị chặn bởi keyword (year_filter): {refuse_df['blocked_by_keyword'].sum()}")
    print(f"  Lọt qua keyword → cần Gate xử lý:  {(~refuse_df['blocked_by_keyword']).sum()}")

    in_scope_df = out_df[out_df['expected_behavior'] != 'refuse']
    print(f"\nTổng câu nhãn in-scope (answer/fallback_warning/...): {len(in_scope_df)}")
    print(f"  Bị chặn bởi keyword (nhầm!): {in_scope_df['blocked_by_keyword'].sum()}")
    print(f"  Lọt qua keyword đúng:         {(~in_scope_df['blocked_by_keyword']).sum()}")

if __name__ == "__main__":
    main()
