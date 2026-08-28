"""
diagnose_gate_multivariate.py — Phân tích đa biến (score_raw, consensus, margin)
trên vùng chồng lấp "dead zone" (0.652–0.871) để đánh giá khả năng tách
refuse vs in-scope bằng rule kết hợp mà không cần LLM.

Đầu ra:
  1. Thống kê phân bố consensus_exact, consensus_file, margin theo nhóm (toàn bộ và trong dead zone).
  2. Thử Logistic Regression đơn giản trên 3 biến (score_raw, consensus_exact, margin).
  3. Decision rule đơn giản: tìm ngưỡng kết hợp tốt nhất qua grid search.
  4. Lưu bảng đầy đủ vào CSV để kiểm tra thủ công.
"""

import sys
import json
import pandas as pd
import numpy as np
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from app.core.index_store import index_store
from app.services.year_filter import analyze
from app.services.retrieval_service import retrieve_with_dynamic_routing

DATA_DIR = r"d:\uth-admission-chatbot\backend\data\test"
DEV_CSV = f"{DATA_DIR}\\dev_questions.csv"
OUT_CSV = r"d:\uth-admission-chatbot\backend\eval\results\gate_multivariate_diagnosis.csv"

DEAD_ZONE_LOW  = 0.652
DEAD_ZONE_HIGH = 0.871


def main():
    print("Nạp index FAISS + BM25...")
    index_store.load()
    print("Nạp index hoàn tất!\n")

    df = pd.read_csv(DEV_CSV)
    rows = []

    print(f"Đang phân tích {len(df)} câu hỏi (thu thập score + consensus + margin)...")
    for _, row in df.iterrows():
        query   = row['user_query']
        behavior = row['expected_behavior']
        category = row['category']

        yr = analyze(query)

        # Bị chặn keyword
        if yr.status == "refused":
            rows.append({
                "query": query[:80],
                "expected_behavior": behavior,
                "category": category,
                "blocked_by_keyword": True,
                "top1_score_raw": None,
                "margin": None,
                "consensus_exact": None,
                "consensus_file":  None,
                "n_chunks": 0,
            })
            continue

        chunks, resp_meta = retrieve_with_dynamic_routing(query, filter_year=yr.filter_year)

        top1_score = chunks[0].score_raw if chunks else None
        top2_score = chunks[1].score_raw if len(chunks) >= 2 else None
        margin = (top1_score - top2_score) if (top1_score is not None and top2_score is not None) else top1_score

        bm25_cid  = resp_meta.get("bm25_top1_cid")
        dense_cid = resp_meta.get("dense_top1_cid")
        bm25_file  = resp_meta.get("bm25_top1_file")
        dense_file = resp_meta.get("dense_top1_file")

        consensus_exact = int(bool(bm25_cid and dense_cid and bm25_cid == dense_cid))
        consensus_file  = int(bool(bm25_file and dense_file and bm25_file == dense_file))

        rows.append({
            "query": query[:80],
            "expected_behavior": behavior,
            "category": category,
            "blocked_by_keyword": False,
            "top1_score_raw": round(top1_score, 6) if top1_score is not None else None,
            "margin": round(margin, 6) if margin is not None else None,
            "consensus_exact": consensus_exact,
            "consensus_file":  consensus_file,
            "n_chunks": len(chunks),
        })

    out_df = pd.DataFrame(rows)
    out_df.to_csv(OUT_CSV, index=False, encoding='utf-8-sig')
    print(f"Đã lưu bảng đầy đủ → {OUT_CSV}\n")

    # -----------------------------------------------------------------------
    # 1. Thống kê toàn bộ (chỉ câu lọt qua year_filter, loại 'redirect')
    # -----------------------------------------------------------------------
    active = out_df[~out_df['blocked_by_keyword'] & (out_df['expected_behavior'] != 'redirect')].copy()
    active['is_refuse'] = (active['expected_behavior'] == 'refuse').astype(int)

    print("=" * 65)
    print("1. PHÂN BỐ TOÀN BỘ (qua year_filter, không kể redirect)")
    print("=" * 65)
    for label in ['answer', 'fallback_warning', 'refuse']:
        grp = active[active['expected_behavior'] == label]
        if grp.empty: continue
        scores = grp['top1_score_raw'].dropna()
        margins = grp['margin'].dropna()
        cons_e = grp['consensus_exact'].dropna()
        cons_f = grp['consensus_file'].dropna()
        print(f"\n[{label}] N={len(grp)}")
        print(f"  score_raw:  min={scores.min():.3f}  P25={scores.quantile(0.25):.3f}  median={scores.median():.3f}  P75={scores.quantile(0.75):.3f}  max={scores.max():.3f}")
        print(f"  margin:     min={margins.min():.3f}  P25={margins.quantile(0.25):.3f}  median={margins.median():.3f}  P75={margins.quantile(0.75):.3f}  max={margins.max():.3f}")
        print(f"  consensus_exact=True: {cons_e.mean()*100:.1f}%  ({int(cons_e.sum())}/{len(cons_e)})")
        print(f"  consensus_file=True:  {cons_f.mean()*100:.1f}%  ({int(cons_f.sum())}/{len(cons_f)})")

    # -----------------------------------------------------------------------
    # 2. Phân tích DEAD ZONE (vùng chồng lấp 0.652 – 0.871)
    # -----------------------------------------------------------------------
    print("\n" + "=" * 65)
    print(f"2. PHÂN TÍCH DEAD ZONE score_raw ∈ [{DEAD_ZONE_LOW}, {DEAD_ZONE_HIGH}]")
    print("=" * 65)
    dz = active[
        active['top1_score_raw'].between(DEAD_ZONE_LOW, DEAD_ZONE_HIGH, inclusive='both')
    ].copy()
    print(f"Số câu trong dead zone: {len(dz)}")
    for label in ['answer', 'fallback_warning', 'refuse']:
        grp = dz[dz['expected_behavior'] == label]
        if grp.empty: continue
        margins = grp['margin'].dropna()
        cons_e = grp['consensus_exact'].dropna()
        cons_f = grp['consensus_file'].dropna()
        scores = grp['top1_score_raw'].dropna()
        print(f"\n  [{label}] N={len(grp)}")
        print(f"    score_raw: P25={scores.quantile(0.25):.3f}  median={scores.median():.3f}  P75={scores.quantile(0.75):.3f}")
        print(f"    margin:    P25={margins.quantile(0.25):.3f}  median={margins.median():.3f}  P75={margins.quantile(0.75):.3f}  mean={margins.mean():.3f}")
        print(f"    consensus_exact=True: {cons_e.mean()*100:.1f}%  ({int(cons_e.sum())}/{len(cons_e)})")
        print(f"    consensus_file=True:  {cons_f.mean()*100:.1f}%  ({int(cons_f.sum())}/{len(cons_f)})")

    # -----------------------------------------------------------------------
    # 3. Logistic Regression đơn giản trên 3 biến
    # -----------------------------------------------------------------------
    print("\n" + "=" * 65)
    print("3. LOGISTIC REGRESSION (score_raw, consensus_exact, margin)")
    print("=" * 65)
    feat_df = active.dropna(subset=['top1_score_raw', 'margin', 'consensus_exact'])
    X = feat_df[['top1_score_raw', 'consensus_exact', 'margin']].values
    y = feat_df['is_refuse'].values

    try:
        from sklearn.linear_model import LogisticRegression
        from sklearn.model_selection import cross_val_score
        from sklearn.preprocessing import StandardScaler

        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        # 5-fold CV để ước tính hiệu năng
        lr = LogisticRegression(class_weight='balanced', random_state=42, max_iter=1000)
        cv_auc = cross_val_score(lr, X_scaled, y, cv=5, scoring='roc_auc')
        cv_recall = cross_val_score(lr, X_scaled, y, cv=5, scoring='recall')
        cv_fpr_inv = cross_val_score(lr, X_scaled, y, cv=5, scoring='precision')

        print(f"5-fold CV AUC (Refuse vs In-scope): {cv_auc.mean():.3f} ± {cv_auc.std():.3f}")
        print(f"5-fold CV Recall (Refuse detected): {cv_recall.mean():.3f} ± {cv_recall.std():.3f}")
        print(f"5-fold CV Precision (1-FPR proxy): {cv_fpr_inv.mean():.3f} ± {cv_fpr_inv.std():.3f}")

        # Fit toàn bộ để xem coefficients
        lr.fit(X_scaled, y)
        print(f"\nCoefficients (score_raw, consensus_exact, margin):")
        for fname, coef in zip(['score_raw', 'consensus_exact', 'margin'], lr.coef_[0]):
            print(f"  {fname}: {coef:+.4f}")
        print(f"  Intercept: {lr.intercept_[0]:+.4f}")
        print(f"  (Giá trị âm → feature cao → thiên về In-scope; dương → thiên về Refuse)")

    except ImportError:
        print("scikit-learn chưa cài. Bỏ qua phần Logistic Regression.")

    # -----------------------------------------------------------------------
    # 4. Grid search decision rule: IF consensus_exact=False AND margin < T_margin
    #    AND score < T_score → refuse
    # -----------------------------------------------------------------------
    print("\n" + "=" * 65)
    print("4. GRID SEARCH DECISION RULE KẾT HỢP (3 tín hiệu)")
    print("   Rule: REFUSE nếu (score < T_s) OR (consensus_exact=False AND score < T_sc)")
    print("=" * 65)

    feat_df2 = active.dropna(subset=['top1_score_raw', 'margin', 'consensus_exact'])
    n_refuse_total = feat_df2[feat_df2['is_refuse'] == 1].shape[0]
    n_in_scope_total = feat_df2[feat_df2['is_refuse'] == 0].shape[0]

    best_recall, best_fpr, best_params = 0.0, 1.0, {}

    # Dạng rule: từ chối nếu score < T_base, HOẶC (consensus=False AND score < T_nc)
    # T_nc >= T_base (ngưỡng không đồng thuận cao hơn)
    score_thresholds  = np.arange(0.60, 0.90, 0.02)
    margin_thresholds = [None, 0.02, 0.04, 0.06, 0.08, 0.10, 0.15, 0.20]

    results_combo = []
    for t_base in score_thresholds:
        for t_nc in score_thresholds:
            if t_nc < t_base: continue  # T_nc phải >= T_base
            for t_m in margin_thresholds:
                refuse_mask = (
                    (feat_df2['top1_score_raw'] < t_base) |
                    ((feat_df2['consensus_exact'] == 0) & (feat_df2['top1_score_raw'] < t_nc))
                )
                if t_m is not None:
                    # Thêm: từ chối nếu margin < t_m (dù score trung bình)
                    refuse_mask = refuse_mask | (feat_df2['margin'] < t_m)

                tp = ((refuse_mask) & (feat_df2['is_refuse'] == 1)).sum()
                fp = ((refuse_mask) & (feat_df2['is_refuse'] == 0)).sum()
                recall = tp / n_refuse_total if n_refuse_total > 0 else 0
                fpr    = fp / n_in_scope_total if n_in_scope_total > 0 else 0

                results_combo.append({
                    "T_base": round(t_base, 2),
                    "T_no_consensus": round(t_nc, 2),
                    "T_margin": t_m,
                    "recall": round(recall, 4),
                    "fpr": round(fpr, 4),
                })

    combo_df = pd.DataFrame(results_combo)

    # Lọc Recall >= 0.90 và FPR thấp nhất
    valid = combo_df[combo_df['recall'] >= 0.90]
    print(f"\nSố tổ hợp đạt Recall ≥ 90%: {len(valid)}")
    if not valid.empty:
        best = valid.sort_values(by='fpr').iloc[0]
        print(f"\n✅ Cấu hình tốt nhất đạt Recall ≥ 90%:")
        print(f"  T_base (ngưỡng cơ bản):           {best['T_base']}")
        print(f"  T_no_consensus (ngưỡng bất đồng): {best['T_no_consensus']}")
        print(f"  T_margin (ngưỡng margin):          {best['T_margin']}")
        print(f"  Recall: {best['recall']*100:.1f}%   FPR: {best['fpr']*100:.1f}%")
    else:
        print("\n❌ Không có tổ hợp nào đạt Recall ≥ 90%.")
        # Hiển thị top 5 recall cao nhất với FPR thấp nhất
        top5 = combo_df.sort_values(by=['recall', 'fpr'], ascending=[False, True]).head(5)
        print("Top 5 tổ hợp tốt nhất:")
        print(top5.to_string(index=False))

    # In thêm: tại ngưỡng recall 80%, FPR tốt nhất là bao nhiêu?
    for r_thresh in [0.90, 0.85, 0.80, 0.75]:
        v = combo_df[combo_df['recall'] >= r_thresh]
        if not v.empty:
            b = v.sort_values(by='fpr').iloc[0]
            print(f"  Recall ≥ {r_thresh*100:.0f}%: FPR min = {b['fpr']*100:.1f}%  "
                  f"(T_base={b['T_base']}, T_nc={b['T_no_consensus']}, T_m={b['T_margin']})")

    # Lưu kết quả combo
    combo_out = r"d:\uth-admission-chatbot\backend\eval\results\gate_combo_grid.csv"
    combo_df.to_csv(combo_out, index=False, encoding='utf-8-sig')
    print(f"\nLưu toàn bộ combo grid → {combo_out}")

    print("\nHOÀN TẤT CHẨN ĐOÁN.")


if __name__ == "__main__":
    main()
