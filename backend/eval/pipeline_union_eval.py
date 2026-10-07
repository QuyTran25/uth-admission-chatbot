"""
pipeline_union_eval.py — Đo lường thực nghiệm pipeline lọc tiền sinh 3 lớp (3-Layer Union Filtering).

Đo lường năng lực lọc câu hỏi ngoài phạm vi trước khi gọi mô hình sinh (Pre-generation):
  Lớp 1: year_filter       (phát hiện năm không hỗ trợ)
  Lớp 2: oos_filter        (phát hiện ý định ngoài phạm vi Hướng C)
  Lớp 3: retrieval_gate    (kiểm soát chất lượng tài liệu hybrid)

Được thiết kế theo nguyên tắc SSoT:
  - Sử dụng chính hàm decide_query từ backend/app/services/pipeline_decision.py (chính là luồng chat.py).
  - Khắc phục triệt để lỗi CD1: Không mô phỏng riêng, không hard-code ngưỡng 0.62.
"""

import sys
import json
import math
import subprocess
import argparse
from pathlib import Path
from typing import Tuple, Optional
import pandas as pd
import numpy as np

# Thêm PROJECT_ROOT vào sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(PROJECT_ROOT / "backend"))

from app.core.index_store import index_store
from app.services.pipeline_decision import decide_query, load_gate_config


def wilson_ci(k: int, n: int, confidence: float = 0.95) -> Tuple[float, float]:
    """Tính Wilson Score Interval 95% cho tỷ lệ k/n."""
    if n <= 0:
        return 0.0, 0.0
    z = 1.959963984540054  # 95% confidence
    p = k / n
    denominator = 1 + z**2 / n
    centre_adjusted_probability = p + z**2 / (2 * n)
    adjusted_std_dev = math.sqrt((p * (1 - p) + z**2 / (4 * n)) / n)
    lower_bound = (centre_adjusted_probability - z * adjusted_std_dev) / denominator
    upper_bound = (centre_adjusted_probability + z * adjusted_std_dev) / denominator
    return max(0.0, float(lower_bound)), min(1.0, float(upper_bound))


def parse_args():
    parser = argparse.ArgumentParser(description="Đánh giá 3 lớp lọc tiền sinh (SSoT)")
    parser.add_argument("--dataset", "--csv", type=str, default="backend/data/test/dev_questions.csv", help="Đường dẫn file câu hỏi test")
    parser.add_argument("--tag", type=str, default="dev", help="Tag nhận diện tập đánh giá (dev, locked, ...)")
    parser.add_argument("--gate-threshold", type=float, default=None, help="Ghi đè threshold_default (chỉ dùng nghiên cứu trên dev)")
    parser.add_argument("--force-gate", action="store_true", help="Cưỡng bức bật Gate (chỉ dùng nghiên cứu trên dev)")
    parser.add_argument("--disable-gate", action="store_true", help="Cưỡng bức tắt Gate (chỉ dùng nghiên cứu trên dev)")
    parser.add_argument("--override-locked-lock", action="store_true", help="Ghi đè khóa an toàn của tập locked")
    return parser.parse_args()


def main():
    args = parse_args()
    data_csv = PROJECT_ROOT / args.dataset
    if not data_csv.exists():
        data_csv = Path(args.dataset)
    if not data_csv.exists():
        raise FileNotFoundError(f"Không tìm thấy file dataset: {args.dataset}")

    is_locked = (args.tag.lower() == "locked" or "locked" in data_csv.name.lower())

    # Khóa an toàn nghiêm ngặt cho tập Locked Holdout
    if is_locked:
        # 1. Cấm các tham số override
        if args.gate_threshold is not None or args.force_gate or args.disable_gate:
            raise ValueError(
                "VI PHẠM NGUYÊN TẮC: Tập Locked là Holdout test set duy nhất! "
                "Cấm tuyệt đối dùng --gate-threshold, --force-gate, hoặc --disable-gate."
            )

        # 2. Yêu cầu workspace Git phải sạch hoàn toàn
        try:
            git_status = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=str(PROJECT_ROOT),
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()
            dirty_lines = [
                line for line in git_status.splitlines()
                if not any(token in line for token in ["results/", "locked_eval_done.json", "pipeline_union_"])
            ]
            if dirty_lines:
                raise RuntimeError(
                    f"VI PHẠM NGUYÊN TẮC: Git workspace chưa commit sạch trước khi chạy Locked set!\n"
                    f"Các file chưa commit:\n" + "\n".join(dirty_lines)
                )
        except Exception as e:
            if "VI PHẠM" in str(e):
                raise
            print(f"[CẢNH BÁO] Không thể kiểm tra git status: {e}")

        # 3. So khớp cấu hình gate_config.json với gate_tuning_dev.json
        dev_tuning_path = PROJECT_ROOT / "backend" / "eval" / "results" / "gate_tuning_dev.json"
        if dev_tuning_path.exists():
            with open(dev_tuning_path, "r", encoding="utf-8") as f:
                dev_tune_data = json.load(f)
            best_cfg = dev_tune_data.get("best_config", {})
            cur_cfg = load_gate_config()

            for key in ["threshold_default", "threshold_consensus", "consensus_type"]:
                if cur_cfg.get(key) != best_cfg.get(key):
                    raise RuntimeError(
                        f"LỆCH CẤU HÌNH: gate_config.json ({key}={cur_cfg.get(key)}) "
                        f"không khớp với best_config trong gate_tuning_dev.json ({key}={best_cfg.get(key)})! "
                        f"Phải đóng băng cấu hình từ Dev trước khi chạy Locked."
                    )
        else:
            print("[CẢNH BÁO] Không tìm thấy gate_tuning_dev.json để kiểm tra chéo cấu hình.")

        # 4. Kiểm tra chốt chặn chạy lại
        lock_file = PROJECT_ROOT / "backend" / "eval" / "results" / "locked_eval_done.json"
        if lock_file.exists() and not args.override_locked_lock:
            raise RuntimeError(
                f"TẬP LOCKED ĐÃ ĐƯỢC ĐÁNH GIÁ TRƯỚC ĐÓ (đã ghi nhận tại {lock_file.name})!\n"
                f"Để bảo vệ tính khách quan của tập kiểm thử kín, cấm chạy lại nhiều lần."
            )

    results_dir = PROJECT_ROOT / "backend" / "eval" / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    out_csv = results_dir / f"pipeline_union_details_{args.tag}.csv"
    summary_json = results_dir / f"pipeline_union_summary_{args.tag}.json"

    # Nạp index tìm kiếm
    print("Nạp index FAISS + BM25...")
    index_store.load()
    print("Nạp index hoàn tất!\n")

    # Xác định cấu hình Gate
    gate_cfg = load_gate_config()
    gate_enabled = gate_cfg.get("enabled", False)

    if args.force_gate:
        gate_enabled = True
    elif args.disable_gate:
        gate_enabled = False

    if args.gate_threshold is not None:
        gate_cfg["threshold_default"] = args.gate_threshold

    gate_cfg["enabled"] = gate_enabled
    print(f"Cấu hình Gate sử dụng: enabled={gate_enabled}, default={gate_cfg.get('threshold_default')}, consensus={gate_cfg.get('threshold_consensus')}, type={gate_cfg.get('consensus_type')}\n")

    df = pd.read_csv(data_csv, encoding="utf-8-sig")
    print(f"Tập đánh giá: {data_csv.name} [Tag: {args.tag}]")
    print(f"Tổng câu hỏi: {len(df)}")
    print(f"Phân bố nhãn:\n{df['expected_behavior'].value_counts().to_string()}\n")

    records = []
    n = len(df)

    for i, row in df.iterrows():
        if (i + 1) % 50 == 0 or (i + 1) == n:
            print(f"  Đang xử lý {i+1}/{n}...")

        query = str(row["user_query"])
        expected = str(row["expected_behavior"])
        qid = row.get("id", i + 1)

        # GỌI TRỰC TIẾP HÀM SSoT CỦA LUỒNG CHAT
        decision = decide_query(
            query=query,
            gate_enabled=gate_enabled,
            gate_config=gate_cfg,
            top_k=5,
        )

        top1_dense = None
        if decision.response_meta and "dense_top1_score" in decision.response_meta:
            top1_dense = decision.response_meta["dense_top1_score"]
        elif decision.chunks:
            top1_dense = decision.chunks[0].score_raw

        records.append({
            "id": qid,
            "user_query": query,
            "expected_behavior": expected,
            "predicted_behavior": decision.behavior,
            "category": row.get("category", ""),
            "intent": row.get("intent", ""),
            "flagged_year_filter": decision.flagged_year_filter,
            "flagged_direction_c": decision.flagged_oos,
            "flagged_gate": decision.flagged_gate,
            "caught_union": (decision.behavior == "refused"),
            "dense_top1_score": round(top1_dense, 5) if top1_dense is not None else None,
            "refused_reason": decision.refused_reason,
            "oos_categories": "|".join(decision.oos_categories),
        })

    out_df = pd.DataFrame(records)
    out_df.to_csv(out_csv, index=False, encoding="utf-8-sig")
    print(f"\nĐã lưu bảng chi tiết → {out_csv}\n")

    # -----------------------------------------------------------------------
    # TÍNH TOÁN METRIC CHUẨN XÁC
    # -----------------------------------------------------------------------
    refuse_mask = out_df["expected_behavior"] == "refuse"
    in_scope_mask = ~refuse_mask

    n_refuse = int(refuse_mask.sum())
    n_in_scope = int(in_scope_mask.sum())

    print(f"Mẫu số chuẩn hóa: Refuse={n_refuse}, In-Scope (non-refuse)={n_in_scope}")
    special_in_scope = out_df[in_scope_mask & ~out_df["expected_behavior"].isin(["answer", "fallback_warning"])]
    if len(special_in_scope) > 0:
        print(f"  * Ghi chú {len(special_in_scope)} câu nhãn đặc biệt thuộc In-Scope:")
        for _, r in special_in_scope.iterrows():
            print(f"    - ID {r['id']} [{r['expected_behavior']}]: {r['user_query'][:60]}")

    print("=" * 75)
    print("METRIC THỰC ĐO TỪNG LỚP VÀ UNION (decide_query)")
    print("=" * 75)

    def report_layer(name, flag_col):
        caught = int((refuse_mask & out_df[flag_col]).sum())
        fp = int((in_scope_mask & out_df[flag_col]).sum())
        recall = caught / n_refuse if n_refuse > 0 else 0.0
        fpr = fp / n_in_scope if n_in_scope > 0 else 0.0
        rec_lo, rec_hi = wilson_ci(caught, n_refuse)
        fpr_lo, fpr_hi = wilson_ci(fp, n_in_scope)
        print(f"  {name:40s}: Recall={caught:3d}/{n_refuse} ({recall*100:5.1f}%, 95% CI [{rec_lo*100:4.1f}%, {rec_hi*100:4.1f}%])  FPR={fp:3d}/{n_in_scope} ({fpr*100:4.2f}%, 95% CI [{fpr_lo*100:4.2f}%, {fpr_hi*100:4.2f}%])")
        return caught, fp, rec_lo, rec_hi, fpr_lo, fpr_hi

    c1, fp1, c1_lo, c1_hi, fp1_lo, fp1_hi = report_layer("Lớp 1 — year_filter", "flagged_year_filter")
    c2_oos, fp2_oos, c2_lo, c2_hi, fp2_lo, fp2_hi = report_layer("Lớp 2 — Hướng C (intent)", "flagged_direction_c")

    # Union 2 lớp đầu
    out_df["caught_2layer"] = out_df["flagged_year_filter"] | out_df["flagged_direction_c"]
    c_u12 = int((refuse_mask & out_df["caught_2layer"]).sum())
    fp_u12 = int((in_scope_mask & out_df["caught_2layer"]).sum())
    rec_u12 = c_u12 / n_refuse if n_refuse > 0 else 0.0
    fpr_u12 = fp_u12 / n_in_scope if n_in_scope > 0 else 0.0
    u12_rec_lo, u12_rec_hi = wilson_ci(c_u12, n_refuse)
    u12_fpr_lo, u12_fpr_hi = wilson_ci(fp_u12, n_in_scope)
    print(f"  {'Union Lớp 1+2':40s}: Recall={c_u12:3d}/{n_refuse} ({rec_u12*100:5.1f}%, 95% CI [{u12_rec_lo*100:4.1f}%, {u12_rec_hi*100:4.1f}%])  FPR={fp_u12:3d}/{n_in_scope} ({fpr_u12*100:4.2f}%, 95% CI [{u12_fpr_lo*100:4.2f}%, {u12_fpr_hi*100:4.2f}%])")

    # Lớp 3: Gate trên phần dư sau L1+L2
    residual_mask = ~out_df["caught_2layer"]
    res_refuse = refuse_mask & residual_mask
    res_in_scope = in_scope_mask & residual_mask
    n_res_refuse = int(res_refuse.sum())
    n_res_in_scope = int(res_in_scope.sum())
    c3 = int((res_refuse & out_df["flagged_gate"]).sum())
    fp3 = int((res_in_scope & out_df["flagged_gate"]).sum())
    rec3 = c3 / n_res_refuse if n_res_refuse > 0 else 0.0
    fpr3 = fp3 / n_res_in_scope if n_res_in_scope > 0 else 0.0
    c3_lo, c3_hi = wilson_ci(c3, n_res_refuse)
    fp3_lo, fp3_hi = wilson_ci(fp3, n_res_in_scope)
    print(f"  {'Lớp 3 — Gate (trên phần dư sau L1+L2)':40s}: Recall={c3:3d}/{n_res_refuse} ({rec3*100:5.1f}%, 95% CI [{c3_lo*100:4.1f}%, {c3_hi*100:4.1f}%])  FPR={fp3:3d}/{n_res_in_scope} ({fpr3*100:4.2f}%, 95% CI [{fp3_lo*100:4.2f}%, {fp3_hi*100:4.2f}%])")

    # Union cả 3 lớp (Thực tế toàn pipeline tiền sinh)
    c_u = int((refuse_mask & out_df["caught_union"]).sum())
    fp_u = int((in_scope_mask & out_df["caught_union"]).sum())
    rec_u = c_u / n_refuse if n_refuse > 0 else 0.0
    fpr_u = fp_u / n_in_scope if n_in_scope > 0 else 0.0
    u_rec_lo, u_rec_hi = wilson_ci(c_u, n_refuse)
    u_fpr_lo, u_fpr_hi = wilson_ci(fp_u, n_in_scope)
    print(f"  {'UNION 3 Lớp (thực đo)':40s}: Recall={c_u:3d}/{n_refuse} ({rec_u*100:5.1f}%, 95% CI [{u_rec_lo*100:4.1f}%, {u_rec_hi*100:4.1f}%])  FPR={fp_u:3d}/{n_in_scope} ({fpr_u*100:4.2f}%, 95% CI [{u_fpr_lo*100:4.2f}%, {u_fpr_hi*100:4.2f}%])")

    # -----------------------------------------------------------------------
    # TÍNH TOÁN EXACT MATCH THEO CẢ 2 PHƯƠNG ÁN (KHÁCH QUAN, KHÔNG CHE GIẤU)
    # -----------------------------------------------------------------------
    valid_exact = out_df[~out_df["expected_behavior"].isin(["redirect"])]
    n_exact = len(valid_exact)

    # 1. Exact Match Strict (4 trạng thái nghiêm ngặt):
    # refuse vs refused, fallback_warning vs fallback_warning, answer vs answer, clarify vs clarify
    def normalize_behavior_strict(b: str) -> str:
        b = str(b).strip().lower()
        if b in ["refuse", "refused"]:
            return "refuse"
        return b

    strict_matches = 0
    for _, r in valid_exact.iterrows():
        exp = normalize_behavior_strict(r["expected_behavior"])
        pred = normalize_behavior_strict(r["predicted_behavior"])
        if exp == pred:
            strict_matches += 1

    strict_acc = strict_matches / n_exact if n_exact > 0 else 0.0

    # 2. Exact Match Merged In-Scope (2-way mapping):
    # Ánh xạ cả 2 chiều: fallback_warning và answer đều thuộc In-Scope
    def normalize_behavior_merged(b: str) -> str:
        b = str(b).strip().lower()
        if b in ["refuse", "refused"]:
            return "refuse"
        if b in ["answer", "fallback_warning"]:
            return "answer"
        return b

    merged_matches = 0
    for _, r in valid_exact.iterrows():
        exp = normalize_behavior_merged(r["expected_behavior"])
        pred = normalize_behavior_merged(r["predicted_behavior"])
        if exp == pred:
            merged_matches += 1

    merged_acc = merged_matches / n_exact if n_exact > 0 else 0.0

    print(f"\n  Exact Match (Strict 4-state):          {strict_matches:3d}/{n_exact} ({strict_acc*100:5.2f}%) [phân biệt rõ fallback_warning vs answer]")
    print(f"  Exact Match (Merged In-Scope 2-way):   {merged_matches:3d}/{n_exact} ({merged_acc*100:5.2f}%) [ánh xạ fallback_warning hai phía]")

    # -----------------------------------------------------------------------
    # PHÂN TÍCH NHÓM SÓT
    # -----------------------------------------------------------------------
    sot_2layer = out_df[res_refuse]
    print(f"\n{'='*75}")
    print(f"CÂU REFUSE SÓT SAU LỚP 1+2: {len(sot_2layer)} câu")
    print(f"{'='*75}")

    sot_scores = sot_2layer["dense_top1_score"].dropna()
    if len(sot_scores) > 0:
        print("Phân bố dense_top1_score nhóm sót:")
        print(f"  Min:    {sot_scores.min():.4f}")
        print(f"  P25:    {sot_scores.quantile(0.25):.4f}")
        print(f"  Median: {sot_scores.median():.4f}")
        print(f"  P75:    {sot_scores.quantile(0.75):.4f}")
        print(f"  Max:    {sot_scores.max():.4f}")

    print("\nDanh sách câu sót:")
    for _, r in sot_2layer.iterrows():
        score_val = f"dense_top1={r['dense_top1_score']:.4f}" if r["dense_top1_score"] is not None else "dense_top1=N/A"
        gate_status = "Gate-CAUGHT" if r["flagged_gate"] else "Gate-MISS"
        print(f"  ID={r['id']:3d}  [{gate_status}]  {score_val}  cat={r['category']}")
        print(f"         {r['user_query'][:75]}")

    # -----------------------------------------------------------------------
    # XUẤT ARTIFACT SUMMARY METRICS JSON
    # -----------------------------------------------------------------------
    summary_data = {
        "dataset": data_csv.name,
        "tag": args.tag,
        "total_queries": len(df),
        "refuse_count": n_refuse,
        "in_scope_count": n_in_scope,
        "gate_config_used": gate_cfg,
        "metrics": {
            "layer1_year_filter": {
                "caught": c1, "total_refuse": n_refuse, "recall": round(c1/n_refuse, 4) if n_refuse else 0,
                "recall_ci_95": [round(c1_lo, 4), round(c1_hi, 4)],
                "fp": fp1, "total_in_scope": n_in_scope, "fpr": round(fp1/n_in_scope, 4) if n_in_scope else 0,
                "fpr_ci_95": [round(fp1_lo, 4), round(fp1_hi, 4)],
            },
            "layer2_oos_intent": {
                "caught": c2_oos, "total_refuse": n_refuse, "recall": round(c2_oos/n_refuse, 4) if n_refuse else 0,
                "recall_ci_95": [round(c2_lo, 4), round(c2_hi, 4)],
                "fp": fp2_oos, "total_in_scope": n_in_scope, "fpr": round(fp2_oos/n_in_scope, 4) if n_in_scope else 0,
                "fpr_ci_95": [round(fp2_lo, 4), round(fp2_hi, 4)],
            },
            "union_layer1_2": {
                "caught": c_u12, "total_refuse": n_refuse, "recall": round(rec_u12, 4),
                "recall_ci_95": [round(u12_rec_lo, 4), round(u12_rec_hi, 4)],
                "fp": fp_u12, "total_in_scope": n_in_scope, "fpr": round(fpr_u12, 4),
                "fpr_ci_95": [round(u12_fpr_lo, 4), round(u12_fpr_hi, 4)],
            },
            "layer3_gate_on_residual": {
                "residual_refuse": n_res_refuse, "caught": c3, "recall": round(rec3, 4),
                "recall_ci_95": [round(c3_lo, 4), round(c3_hi, 4)],
                "residual_in_scope": n_res_in_scope, "fp": fp3, "fpr": round(fpr3, 4),
                "fpr_ci_95": [round(fp3_lo, 4), round(fp3_hi, 4)],
            },
            "union_full_pipeline": {
                "caught": c_u, "total_refuse": n_refuse, "recall": round(rec_u, 4),
                "recall_ci_95": [round(u_rec_lo, 4), round(u_rec_hi, 4)],
                "fp": fp_u, "total_in_scope": n_in_scope, "fpr": round(fpr_u, 4),
                "fpr_ci_95": [round(u_fpr_lo, 4), round(u_fpr_hi, 4)],
            },
            "exact_match_strict": {
                "correct": strict_matches, "total": n_exact, "accuracy": round(strict_acc, 4)
            },
            "exact_match_merged": {
                "correct": merged_matches, "total": n_exact, "accuracy": round(merged_acc, 4)
            }
        }
    }

    with open(summary_json, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=4, ensure_ascii=False)
    print(f"\nĐã lưu summary metrics → {summary_json}")

    # Đóng dấu hoàn tất cho Locked Set
    if is_locked:
        lock_file = results_dir / "locked_eval_done.json"
        with open(lock_file, "w", encoding="utf-8") as f:
            json.dump({
                "status": "COMPLETED",
                "tag": args.tag,
                "dataset": data_csv.name,
                "summary": summary_data,
            }, f, indent=4, ensure_ascii=False)
        print(f"ĐÃ LẬP CHỐT KHÓA TẬP LOCKED TẠI: {lock_file} (Chỉ được chạy một lần)")

    print("\nHOÀN TẤT PIPELINE UNION EVAL.")


if __name__ == "__main__":
    main()
