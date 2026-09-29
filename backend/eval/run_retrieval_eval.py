"""
run_retrieval_eval.py — Thực nghiệm Đánh giá Hiệu năng Retrieval với Bootstrap CI và Kiểm định So cặp.

Giải quyết triệt để Feedback #1, #2, #3 của Giảng viên:
  - #1: Tách bạch hoàn toàn đánh giá trên Dev Set (390 câu) và Locked Set (100 câu).
  - #2: Đối chiếu Gold Chunk với Index canonical, tính metric trên tập hợp lệ và tập đã ánh xạ chuẩn.
  - #3: Đưa alpha về SSoT (settings.DENSE_WEIGHT), bổ sung 95% Bootstrap CI và kiểm định so cặp (Paired Test)
        giữa Weighted vs RRF, Dense-only, BM25-only; ghi rõ phạm vi khảo sát mô hình embedding.

Chạy:
  python backend/eval/run_retrieval_eval.py --dataset backend/data/test/dev_questions.csv --tag dev
  python backend/eval/run_retrieval_eval.py --dataset backend/data/test/test_questions_locked.csv --tag locked
"""

import os
import sys
import time
import json
import logging
import argparse
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional

import numpy as np
import pandas as pd
from scipy import stats

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("retrieval_eval")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(PROJECT_ROOT / "backend"))

from app.core.config import settings
from app.core.index_store import index_store
from app.services.retrieval_service import (
    search_bm25,
    search_dense,
    search_hybrid,
    ScoredChunk,
)
from eval.audit_gold_chunks import CANONICAL_REPLACEMENTS, load_valid_index_chunks, INDEX_META_PATH


def bootstrap_ci(
    values: List[float],
    n_resamples: int = 1000,
    ci_level: float = 0.95,
    seed: int = 42
) -> Tuple[float, float, float]:
    """Tính mean và khoảng tin cậy Bootstrap 95% [lower, upper]."""
    if not values:
        return 0.0, 0.0, 0.0
    arr = np.array(values, dtype=float)
    if len(arr) == 1:
        return float(arr[0]), float(arr[0]), float(arr[0])
    
    rng = np.random.default_rng(seed)
    boot_means = np.empty(n_resamples)
    n = len(arr)
    for i in range(n_resamples):
        sample = rng.choice(arr, size=n, replace=True)
        boot_means[i] = sample.mean()

    alpha = 1.0 - ci_level
    low = np.percentile(boot_means, alpha / 2 * 100)
    high = np.percentile(boot_means, (1 - alpha / 2) * 100)
    return float(arr.mean()), float(low), float(high)


def paired_comparison_test(a_vals: List[float], b_vals: List[float]) -> Dict[str, float]:
    """
    Kiểm định so cặp (Paired Test) giữa hai phương pháp trên cùng danh sách truy vấn.
    Tính mean difference, t-statistic, paired t-test p-value, và Wilcoxon signed-rank p-value.
    """
    if len(a_vals) != len(b_vals) or len(a_vals) == 0:
        return {"delta_mean": 0.0, "p_ttest": 1.0, "p_wilcoxon": 1.0}

    a = np.array(a_vals, dtype=float)
    b = np.array(b_vals, dtype=float)
    diff = a - b
    delta_mean = float(diff.mean())

    # Paired t-test
    if np.all(diff == 0):
        p_ttest = 1.0
        p_wilcoxon = 1.0
    else:
        try:
            _, p_ttest = stats.ttest_rel(a, b)
        except Exception:
            p_ttest = 1.0

        try:
            # wilcoxon requires non-zero differences
            nonzero = diff[diff != 0]
            if len(nonzero) >= 5:
                _, p_wilcoxon = stats.wilcoxon(nonzero)
            else:
                p_wilcoxon = 1.0
        except Exception:
            p_wilcoxon = 1.0

    return {
        "delta_mean": float(delta_mean),
        "p_ttest": float(p_ttest) if not np.isnan(p_ttest) else 1.0,
        "p_wilcoxon": float(p_wilcoxon) if not np.isnan(p_wilcoxon) else 1.0
    }


def calculate_metrics(rank: Optional[int], k_list: List[int] = [1, 3, 5, 10]) -> Tuple[Dict[int, float], float]:
    recall_at_k = {}
    if rank is not None and rank > 0:
        rr = 1.0 / rank
        for k in k_list:
            recall_at_k[k] = 1.0 if rank <= k else 0.0
    else:
        rr = 0.0
        for k in k_list:
            recall_at_k[k] = 0.0
    return recall_at_k, rr


def evaluate_single_retrieval(
    query: str,
    target_cid: str,
    filters: dict,
    method: str,
    top_k: int = 10,
    alpha: Optional[float] = None,
) -> Tuple[Optional[int], float, Optional[str]]:
    try:
        if method == "BM25":
            results, _ = search_bm25(query, top_k=top_k, filters=filters)
        elif method == "Dense":
            results, _ = search_dense(query, top_k=top_k, filters=filters)
        elif method == "Hybrid_RRF":
            results, _ = search_hybrid(query, top_k=top_k, filters=filters, fusion_method="rrf")
        elif method == "Hybrid_Weighted":
            results, _ = search_hybrid(
                query, top_k=top_k, filters=filters, fusion_method="weighted", alpha=alpha
            )
        else:
            raise ValueError(f"Unknown method: {method}")
    except Exception as e:
        logger.error(f"Lỗi retrieval method={method}: {e}")
        return None, 0.0, None

    rank = None
    for idx, chunk in enumerate(results):
        if chunk.chunk_id == target_cid:
            rank = idx + 1
            break

    top1_score = results[0].score if results else 0.0
    top1_cid = results[0].chunk_id if results else None
    return rank, top1_score, top1_cid


def map_canonical_chunk(cid: str, query: str, fact: str) -> str:
    for (bad_cid, token), good_cid in CANONICAL_REPLACEMENTS.items():
        if cid == bad_cid and (token in fact or token in query):
            return good_cid
    return cid


def main():
    parser = argparse.ArgumentParser(description="Run retrieval evaluation with Bootstrap CI and paired tests")
    parser.add_argument("--dataset", type=str, default="backend/data/test/dev_questions.csv")
    parser.add_argument("--tag", type=str, default="dev", help="Tag for output files: dev or locked")
    parser.add_argument("--protocol", type=str, default="canonical_mapped", choices=["canonical_mapped", "valid_only", "raw"])
    args = parser.parse_args()

    results_dir = PROJECT_ROOT / "backend" / "eval" / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    csv_path = PROJECT_ROOT / args.dataset
    if not csv_path.exists():
        logger.error(f"Dataset file not found: {csv_path}")
        return

    logger.info("Nạp canonical IndexStore...")
    index_store.load()
    canonical_chunks = load_valid_index_chunks(INDEX_META_PATH)
    logger.info(f"Nạp index thành công: {len(canonical_chunks)} chunks.")

    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    logger.info(f"Đã nạp {len(df)} dòng từ {csv_path.name}")

    # Chỉ đánh giá các câu có nhu cầu retrieval (in_scope và year_control)
    # Câu refuse / out_of_scope được đo bởi bộ lọc OOS, không tính vào retrieval accuracy
    eval_mask = (df["expected_behavior"] != "refuse") & (df["category"] != "out_of_scope")
    eval_df = df[eval_mask].copy()

    logger.info(f"Số câu in-scope/year-control cần retrieval: {len(eval_df)}/{len(df)}")

    # Xử lý target chunk theo protocol
    effective_targets = []
    is_valid_list = []
    for _, row in eval_df.iterrows():
        raw_cid = str(row["chunk_id"]).strip() if pd.notna(row["chunk_id"]) else ""
        query = str(row["user_query"])
        fact = str(row.get("core_fact", ""))

        if args.protocol == "canonical_mapped":
            mapped_cid = map_canonical_chunk(raw_cid, query, fact)
        elif args.protocol == "valid_only":
            mapped_cid = raw_cid if raw_cid in canonical_chunks else ""
        else: # raw
            mapped_cid = raw_cid

        effective_targets.append(mapped_cid)
        is_valid_list.append(mapped_cid in canonical_chunks)

    eval_df["target_cid"] = effective_targets
    eval_df["is_valid_gold"] = is_valid_list

    if args.protocol == "valid_only":
        eval_df = eval_df[eval_df["is_valid_gold"]].copy()
        logger.info(f"Protocol valid_only: giữ lại {len(eval_df)} câu có target chunk hợp lệ.")

    # Cấu hình các phương pháp
    ssot_alpha = settings.DENSE_WEIGHT
    methods = [
        {"name": "BM25", "alpha": None},
        {"name": "Dense", "alpha": None},
        {"name": "Hybrid_RRF", "alpha": None},
        {"name": "Hybrid_Weighted", "alpha": ssot_alpha},
    ]

    modes = ["No-Filter", "Filter"]
    k_list = [1, 3, 5, 10]

    # Lưu kết quả per-query để tính bootstrap CI và paired test
    # (mode, method) -> list of RR, list of R@1, list of R@3, list of R@5, list of R@10
    query_results = {}
    for mode in modes:
        for m in methods:
            query_results[(mode, m["name"])] = {
                "rr": [],
                1: [],
                3: [],
                5: [],
                10: []
            }

    logger.info(f"Bắt đầu chạy đánh giá retrieval [Tag: {args.tag}, Protocol: {args.protocol}, SSoT Alpha: {ssot_alpha}]...")

    for mode in modes:
        logger.info(f"--- Đang chạy chế độ: {mode} Mode ---")
        for idx, (_, row) in enumerate(eval_df.iterrows()):
            query = row["user_query"]
            target_cid = row["target_cid"]

            filters = {}
            if mode == "No-Filter":
                filters["admission_year"] = "all"
            else:
                q_year = row.get("admission_year")
                if pd.notna(q_year) and str(q_year).strip() != "":
                    try:
                        filters["admission_year"] = int(float(q_year))
                    except Exception:
                        pass

            for m in methods:
                method_name = m["name"]
                alpha = m["alpha"]

                if not target_cid or target_cid not in canonical_chunks:
                    rank = None
                else:
                    rank, _, _ = evaluate_single_retrieval(
                        query=query,
                        target_cid=target_cid,
                        filters=filters,
                        method=method_name,
                        top_k=10,
                        alpha=alpha,
                    )

                recall_k, rr = calculate_metrics(rank, k_list)
                acc = query_results[(mode, method_name)]
                acc["rr"].append(rr)
                for k in k_list:
                    acc[k].append(recall_k[k])

            if (idx + 1) % 50 == 0:
                logger.info(f"  Đã xử lý {idx + 1}/{len(eval_df)} câu...")

    # Tổng hợp bảng metrics + Bootstrap CI 95%
    summary_rows = []
    for mode in modes:
        for m in methods:
            m_name = m["name"]
            data = query_results[(mode, m_name)]
            mrr_mean, mrr_low, mrr_high = bootstrap_ci(data["rr"])
            r1_mean, r1_low, r1_high = bootstrap_ci(data[1])
            r3_mean, r3_low, r3_high = bootstrap_ci(data[3])
            r5_mean, r5_low, r5_high = bootstrap_ci(data[5])
            r10_mean, r10_low, r10_high = bootstrap_ci(data[10])

            summary_rows.append({
                "Mode": mode,
                "Method": m_name,
                "N": len(data["rr"]),
                "MRR": round(mrr_mean, 4),
                "MRR_CI95": f"[{mrr_low:.4f}, {mrr_high:.4f}]",
                "Recall@1": round(r1_mean, 4),
                "Recall@1_CI95": f"[{r1_low:.4f}, {r1_high:.4f}]",
                "Recall@3": round(r3_mean, 4),
                "Recall@5": round(r5_mean, 4),
                "Recall@5_CI95": f"[{r5_low:.4f}, {r5_high:.4f}]",
                "Recall@10": round(r10_mean, 4),
            })

    summary_df = pd.DataFrame(summary_rows)

    # Tính Paired Comparison Test cho Hybrid Weighted (SSoT) vs các phương pháp khác
    paired_rows = []
    for mode in modes:
        hw_rr = query_results[(mode, "Hybrid_Weighted")]["rr"]
        for comp_name in ["Hybrid_RRF", "Dense", "BM25"]:
            comp_rr = query_results[(mode, comp_name)]["rr"]
            test_res = paired_comparison_test(hw_rr, comp_rr)
            paired_rows.append({
                "Mode": mode,
                "Comparison": f"Hybrid_Weighted vs {comp_name}",
                "Delta_MRR": round(test_res["delta_mean"], 4),
                "p_value_ttest": f"{test_res['p_ttest']:.4e}" if test_res['p_ttest'] < 0.001 else f"{test_res['p_ttest']:.4f}",
                "p_value_wilcoxon": f"{test_res['p_wilcoxon']:.4e}" if test_res['p_wilcoxon'] < 0.001 else f"{test_res['p_wilcoxon']:.4f}",
                "Statistically_Significant_p05": "Có (p < 0.05)" if test_res["p_ttest"] < 0.05 else "Không (p >= 0.05)"
            })

    paired_df = pd.DataFrame(paired_rows)

    # Lưu JSON và Markdown
    out_json_path = results_dir / f"retrieval_eval_{args.tag}.json"
    out_md_path = results_dir / f"retrieval_eval_{args.tag}.md"

    final_payload = {
        "dataset": args.dataset,
        "tag": args.tag,
        "protocol": args.protocol,
        "total_in_scope_evaluated": len(eval_df),
        "ssot_alpha": ssot_alpha,
        "summary_metrics": summary_rows,
        "paired_tests": paired_rows,
    }
    out_json_path.write_text(json.dumps(final_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    # Tạo file Markdown chuyên nghiệp phục vụ Bảng 5.1
    md_lines = [
        f"# Kết quả Thực nghiệm Retrieval — {args.tag.upper()} SET",
        "",
        "> [!IMPORTANT]",
        f"**Thông tin thực nghiệm:**",
        f"- **Tập dữ liệu:** `{args.dataset}` ({len(eval_df)} câu in-scope/year-control).",
        f"- **Quy chuẩn đối soát (Protocol):** `{args.protocol}`.",
        f"- **Cấu hình Alpha SSoT:** `settings.DENSE_WEIGHT = {ssot_alpha}` (Dense {ssot_alpha}, BM25 {1 - ssot_alpha:.1f}).",
        f"- **Bootstrap Resampling:** 1,000 lần (Khoảng tin cậy 95% hai phía).",
        "",
        "## 1. Bảng 5.1 Tái lập: Hiệu năng Retrieval kèm Bootstrap CI 95%",
        "",
        "| Chế độ | Phương pháp | MRR (Mean) | MRR 95% CI | Recall@1 | Recall@1 95% CI | Recall@3 | Recall@5 | Recall@5 95% CI | Recall@10 |",
        "|---|---|---:|:---:|---:|:---:|---:|---:|:---:|---:|"
    ]

    for _, r in summary_df.iterrows():
        md_lines.append(
            f"| {r['Mode']} | {r['Method']} | {r['MRR']:.4f} | {r['MRR_CI95']} | "
            f"{r['Recall@1']:.4f} | {r['Recall@1_CI95']} | {r['Recall@3']:.4f} | "
            f"{r['Recall@5']:.4f} | {r['Recall@5_CI95']} | {r['Recall@10']:.4f} |"
        )

    md_lines.extend([
        "",
        "## 2. Kiểm định Thống kê So cặp (Paired Significance Testing)",
        "",
        "Đánh giá xem chênh lệch giữa **Hybrid Weighted** và các phương pháp khác có ý nghĩa thống kê hay không:",
        "",
        "| Chế độ | Cặp so sánh | Δ MRR | p-value (Paired t-test) | p-value (Wilcoxon) | Ý nghĩa (α=0.05) |",
        "|---|---|---:|---:|---:|:---:|"
    ])

    for _, r in paired_df.iterrows():
        md_lines.append(
            f"| {r['Mode']} | {r['Comparison']} | {r['Delta_MRR']:+.4f} | "
            f"{r['p_value_ttest']} | {r['p_value_wilcoxon']} | {r['Statistically_Significant_p05']} |"
        )

    md_lines.extend([
        "",
        "## 3. Khảo sát Mô hình Embedding (Embedding Comparison Scope)",
        "",
        "> [!NOTE]",
        "**Minh bạch hóa phạm vi mô hình embedding:**",
        "- **Mô hình chính thức sử dụng:** `bkai-foundation-models/vietnamese-bi-encoder` (768 chiều).",
        "- **Lý do không so sánh trực tiếp BGE-M3:** Toàn bộ cơ sở dữ liệu vector hiện tại (`faiss.index`) được lập chỉ mục ở không gian 768 chiều. Mô hình BGE-M3 sinh vector 1024 chiều, dẫn đến lỗi xung đột chiều không gian (Dimension Mismatch) khi truy vấn trên index có sẵn. Để so sánh chuẩn mực cần xây dựng một index 1024 chiều song song. Do đó, trong báo cáo này, chúng tôi **ghi nhận rõ ràng là chưa so sánh đa mô hình embedding**, mà tập trung vào tối ưu hóa chiến lược kết hợp (Fusion Strategy) trên cùng một không gian embedding cơ sở.",
        ""
    ])

    out_md_path.write_text("\n".join(md_lines), encoding="utf-8")
    logger.info(f"Đã lưu kết quả tại: {out_md_path}")
    logger.info(f"Đã lưu JSON tại: {out_json_path}")


if __name__ == "__main__":
    main()
