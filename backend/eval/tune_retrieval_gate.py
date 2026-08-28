"""
tune_retrieval_gate.py — Script hiệu chỉnh ngưỡng Retrieval Gate trên tập dev.

Các bước thực hiện:
1. Đọc tập dev (dev_questions.csv).
2. Chạy year_filter + retrieve_with_dynamic_routing để thu thập kết quả tìm kiếm trước (tiết kiệm tài nguyên).
3. Grid Search tối ưu các tham số:
   - consensus_type: ['exact', 'file']
   - threshold_default: 0.1 đến 0.8 (step 0.02)
   - threshold_consensus: 0.1 đến threshold_default (step 0.02)
   - margin_threshold: [None, 0.02, 0.04, 0.06, 0.08, 0.10]
4. Chọn cấu hình tối ưu theo tiêu chí:
   - Đạt Refusal Recall >= 90%.
   - Có FPR (Over-refusal) thấp nhất.
   - Tiêu chí margin: Giảm FPR >= 2% mới dùng.
5. Đánh giá kiểm chứng chênh lệch hiệu năng trên Hold-out Test Set (test_questions_locked.csv) để phát hiện overfitting.
6. Lưu cấu hình tối ưu vào file backend/app/core/gate_config.json.
"""

import os
import sys
import pandas as pd
import numpy as np
from pathlib import Path
import json
import time

sys.path.append(str(Path(__file__).parent.parent))

from app.core.index_store import index_store
from app.services.year_filter import analyze
from app.services.retrieval_service import retrieve_with_dynamic_routing
from app.services.retrieval_gate import check_retrieval_quality

DATA_DIR = r"d:\uth-admission-chatbot\backend\data\test"
DEV_CSV = os.path.join(DATA_DIR, "dev_questions.csv")
TEST_LOCKED_CSV = os.path.join(DATA_DIR, "test_questions_locked.csv")
CONFIG_OUT_PATH = r"d:\uth-admission-chatbot\backend\app\core\gate_config.json"


def precompute_retrieval(csv_path: str) -> list:
    """Chạy retrieval trước cho toàn bộ câu hỏi trong file CSV để tăng tốc độ grid search."""
    df = pd.read_csv(csv_path)
    records = []
    
    print(f"Bắt đầu tiền truy xuất (precompute retrieval) cho {len(df)} câu từ {os.path.basename(csv_path)}...")
    start_time = time.time()
    
    for idx, row in df.iterrows():
        query = row['user_query']
        behavior = row['expected_behavior']
        category = row['category']
        qid = row['id']
        
        # 1. Chạy year_filter
        yr = analyze(query)
        
        # 2. Nếu year_filter từ chối
        if yr.status == "refused":
            records.append({
                "id": qid,
                "query": query,
                "expected_behavior": behavior,
                "category": category,
                "blocked_by_keyword": True,
                "yr_refusal_source": yr.refusal_source,
                "chunks": [],
                "resp_meta": {}
            })
        else:
            # 3. Chạy retrieval
            chunks, resp_meta = retrieve_with_dynamic_routing(query, filter_year=yr.filter_year)
            records.append({
                "id": qid,
                "query": query,
                "expected_behavior": behavior,
                "category": category,
                "blocked_by_keyword": False,
                "yr_refusal_source": None,
                "chunks": chunks,
                "resp_meta": resp_meta
            })
            
    print(f"Tiền truy xuất hoàn tất trong {time.time() - start_time:.2f} giây.")
    return records


def evaluate_config(
    records: list,
    threshold_default: float,
    threshold_consensus: float,
    consensus_type: str,
    margin_threshold: float
) -> tuple:
    """Đánh giá Recall và FPR tổng thể (cả keyword + gate) của một cấu hình."""
    n_refuse = sum(1 for r in records if r["expected_behavior"] == "refuse")
    n_in_scope = sum(1 for r in records if r["expected_behavior"] != "refuse")
    
    refuse_blocked = 0
    in_scope_blocked_nham = 0
    
    for r in records:
        expected = r["expected_behavior"]
        is_refuse_label = (expected == "refuse")
        
        # Nếu bị chặn bởi keyword từ trước
        if r["blocked_by_keyword"]:
            if is_refuse_label:
                refuse_blocked += 1
            else:
                in_scope_blocked_nham += 1
            continue
            
        # Nếu đi tiếp vào Gate
        gate_status, _ = check_retrieval_quality(
            chunks=r["chunks"],
            response_meta=r["resp_meta"],
            threshold_default=threshold_default,
            threshold_consensus=threshold_consensus,
            consensus_type=consensus_type,
            margin_threshold=margin_threshold
        )
        
        if gate_status == "refused":
            if is_refuse_label:
                refuse_blocked += 1
            else:
                in_scope_blocked_nham += 1
                
    recall = refuse_blocked / n_refuse if n_refuse > 0 else 1.0
    fpr = in_scope_blocked_nham / n_in_scope if n_in_scope > 0 else 0.0
    
    return recall, fpr


def run_grid_search(records: list) -> pd.DataFrame:
    """Quét toàn bộ không gian tham số để đánh giá hiệu năng."""
    results = []
    
    consensus_types = ["exact", "file"]
    # Quét ngưỡng từ 0.1 đến 0.8 với bước 0.02
    threshold_defaults = np.arange(0.1, 0.82, 0.02)
    margin_thresholds = [None, 0.02, 0.04, 0.06, 0.08, 0.10]
    
    total_iters = 0
    # Tính tổng số iter để báo cáo
    for td in threshold_defaults:
        threshold_consensuses = np.arange(0.1, td + 0.01, 0.02)
        total_iters += len(threshold_consensuses)
    total_iters *= len(consensus_types) * len(margin_thresholds)
    print(f"Bắt đầu Grid Search với {total_iters} tổ hợp tham số...")
    
    start_time = time.time()
    
    for consensus in consensus_types:
        for td in threshold_defaults:
            # Ngưỡng đồng thuận phải nhỏ hơn hoặc bằng ngưỡng mặc định
            threshold_consensuses = np.arange(0.1, td + 0.01, 0.02)
            for tc in threshold_consensuses:
                for margin in margin_thresholds:
                    rec, fpr = evaluate_config(records, td, tc, consensus, margin)
                    results.append({
                        "consensus_type": consensus,
                        "threshold_default": round(td, 4),
                        "threshold_consensus": round(tc, 4),
                        "margin_threshold": margin,
                        "recall": round(rec, 4),
                        "fpr": round(fpr, 4)
                    })
                    
    print(f"Grid Search hoàn tất trong {time.time() - start_time:.2f} giây.")
    return pd.DataFrame(results)


def main():
    # 0. Nạp FAISS + BM25 index vào bộ nhớ (BẮT BUỘC trước khi gọi retrieval)
    print("Đang nạp index FAISS và BM25 vào bộ nhớ...")
    index_store.load()
    print("Nạp index hoàn tất!\n")

    # 1. Chạy tiền truy xuất cho tập Dev
    dev_records = precompute_retrieval(DEV_CSV)
    
    # 2. Grid Search trên tập Dev
    df_results = run_grid_search(dev_records)
    
    # 3. Phân tích kết quả
    # Lọc các cấu hình đạt Recall >= 90% (0.90)
    df_valid = df_results[df_results['recall'] >= 0.90]
    
    if df_valid.empty:
        print("Cảnh báo: Không có cấu hình nào đạt Recall >= 90% trên tập dev. Lấy cấu hình có Recall cao nhất.")
        max_recall = df_results['recall'].max()
        df_valid = df_results[df_results['recall'] == max_recall]
        
    # Cấu hình tốt nhất KHÔNG dùng Margin
    df_no_margin = df_valid[df_valid['margin_threshold'].isna()]
    best_no_margin = df_no_margin.sort_values(by='fpr', ascending=True).iloc[0] if not df_no_margin.empty else None
    
    # Cấu hình tốt nhất CÓ dùng Margin (không phải None)
    df_with_margin = df_valid[~df_valid['margin_threshold'].isna()]
    best_with_margin = df_with_margin.sort_values(by='fpr', ascending=True).iloc[0] if not df_with_margin.empty else None
    
    # Quyết định tích hợp Margin:
    # Nếu FPR của cấu hình có margin giảm ít nhất 2% (0.02) so với cấu hình không dùng margin
    use_margin = False
    best_config = best_no_margin
    
    if best_with_margin is not None and best_no_margin is not None:
        margin_fpr_improvement = best_no_margin['fpr'] - best_with_margin['fpr']
        print(f"\nSo sánh hiệu năng Margin:")
        print(f"  - Tốt nhất KHÔNG Margin: Recall={best_no_margin['recall']:.2%}, FPR={best_no_margin['fpr']:.2%}")
        print(f"  - Tốt nhất CÓ Margin: Recall={best_with_margin['recall']:.2%}, FPR={best_with_margin['fpr']:.2%} (margin={best_with_margin['margin_threshold']})")
        print(f"  - Chênh lệch FPR cải thiện: {margin_fpr_improvement:.2%}")
        
        if margin_fpr_improvement >= 0.02:
            print("=> Đồng ý tích hợp Margin (FPR cải thiện >= 2%).")
            use_margin = True
            best_config = best_with_margin
        else:
            print("=> Không tích hợp Margin (Cải thiện FPR < 2%, ưu tiên cấu hình tối giản).")
    elif best_with_margin is not None:
        best_config = best_with_margin
        use_margin = True
        print("\nChỉ tìm thấy cấu hình hợp lệ có dùng Margin.")
        
    print("\n=== CẤU HÌNH TỐI ƯU CHỌN ĐƯỢC TRÊN TẬP DEV ===")
    print(f"Consensus Type: {best_config['consensus_type']}")
    print(f"Ngưỡng Default: {best_config['threshold_default']}")
    print(f"Ngưỡng Consensus: {best_config['threshold_consensus']}")
    print(f"Margin Ngưỡng: {best_config['margin_threshold']}")
    print(f"Hiệu năng trên Dev: Recall={best_config['recall']:.2%}, FPR (Over-refusal)={best_config['fpr']:.2%}")
    
    # 4. Lưu cấu hình tối ưu vào file json
    gate_config = {
        "consensus_type": str(best_config['consensus_type']),
        "threshold_default": float(best_config['threshold_default']),
        "threshold_consensus": float(best_config['threshold_consensus']),
        "margin_threshold": float(best_config['margin_threshold']) if pd.notna(best_config['margin_threshold']) else None
    }
    with open(CONFIG_OUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(gate_config, f, indent=4, ensure_ascii=False)
    print(f"Đã ghi cấu hình vào: {CONFIG_OUT_PATH}")
    
    # 5. Chạy Đánh giá Độc lập trên Hold-out Test Set (được khóa)
    print("\n" + "="*50)
    print("ĐÁNH GIÁ ĐỘC LẬP TRÊN HOLD-OUT TEST SET (ĐÃ KHÓA)")
    print("="*50)
    
    test_records = precompute_retrieval(TEST_LOCKED_CSV)
    test_recall, test_fpr = evaluate_config(
        test_records,
        threshold_default=gate_config["threshold_default"],
        threshold_consensus=gate_config["threshold_consensus"],
        consensus_type=gate_config["consensus_type"],
        margin_threshold=gate_config["margin_threshold"]
    )
    
    print(f"\nKết quả đối chiếu:")
    print(f"  - Tập Dev (Tuning):    Recall={best_config['recall']:.2%}, FPR={best_config['fpr']:.2%}")
    print(f"  - Tập Test Khóa (Hold): Recall={test_recall:.2%}, FPR={test_fpr:.2%}")
    
    diff_recall = best_config['recall'] - test_recall
    diff_fpr = test_fpr - best_config['fpr']
    
    print(f"  - Độ lệch (Test - Dev): Recall={-diff_recall:.2%}, FPR={diff_fpr:.2%}")
    if abs(diff_recall) > 0.05 or abs(diff_fpr) > 0.05:
        print("WARNING: Phát hiện độ chênh lệch hiệu năng lớn (> 5%) giữa Dev và Test. Đây có thể là dấu hiệu overfitting ngưỡng vào Dev Set. Cần ghi nhận hạn chế này trong báo cáo.")
    else:
        print("INFO: Độ chênh lệch hiệu năng nằm trong phạm vi an toàn (<= 5%). Ngưỡng có tính tổng quát hóa tốt.")

if __name__ == "__main__":
    main()
