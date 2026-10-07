"""
compile_metrics.py — Tổng hợp metrics_runtime.json và metrics_retrieval.json
Đọc 100% dữ liệu từ file kết quả chạy thực nghiệm:
  - pipeline_union_summary_dev.json
  - pipeline_union_summary_locked.json
  - ablation_study_locked.json
  - retrieval_eval_dev.json
  - retrieval_eval_locked.json

Tuyệt đối KHÔNG hard-code số liệu ảo. Nếu file chưa có thì báo rõ trạng thái "Chưa thực thi".
"""

import json
from pathlib import Path

RESULTS_DIR = Path(__file__).resolve().parent / "results"
GATE_CONFIG_PATH = Path(__file__).resolve().parent.parent / "core" / "gate_config.json"


def compile_retrieval_metrics():
    dev_path = RESULTS_DIR / "retrieval_eval_dev.json"
    locked_path = RESULTS_DIR / "retrieval_eval_locked.json"

    dev_data = {}
    locked_data = {}

    if dev_path.exists():
        with open(dev_path, "r", encoding="utf-8") as f:
            dev_data = json.load(f)

    if locked_path.exists():
        with open(locked_path, "r", encoding="utf-8") as f:
            locked_data = json.load(f)

    metrics_retrieval = {
        "title": "Comprehensive Retrieval Benchmark (R1) - Dev and Locked Sets",
        "protocol": "canonical_mapped",
        "ssot_dense_weight": dev_data.get("ssot_alpha", 0.6) if dev_data else 0.6,
        "dev_set": {
            "dataset": dev_data.get("dataset", "dev_questions.csv"),
            "sample_size_in_scope": dev_data.get("total_in_scope_evaluated"),
            "year_detection_accuracy": dev_data.get("year_detection_accuracy"),
            "summary_metrics": dev_data.get("summary_metrics"),
            "paired_tests": dev_data.get("paired_tests"),
        } if dev_data else {"status": "Chưa chạy retrieval eval trên dev"},
        "locked_set": {
            "dataset": locked_data.get("dataset", "test_questions_locked.csv"),
            "sample_size_in_scope": locked_data.get("total_in_scope_evaluated"),
            "year_detection_accuracy": locked_data.get("year_detection_accuracy"),
            "summary_metrics": locked_data.get("summary_metrics"),
            "paired_tests": locked_data.get("paired_tests"),
        } if locked_data else {"status": "Chưa chạy retrieval eval trên locked"},
    }

    out_file = RESULTS_DIR / "metrics_retrieval.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(metrics_retrieval, f, indent=2, ensure_ascii=False)
    print(f"Đã xuất: {out_file}")


def compile_runtime_metrics():
    # 1. Đọc Gate Config hiện tại
    gate_cfg = {}
    if GATE_CONFIG_PATH.exists():
        with open(GATE_CONFIG_PATH, "r", encoding="utf-8") as f:
            gate_cfg = json.load(f)

    # 2. Đọc kết quả tuning dev (nếu có)
    gate_tune_path = RESULTS_DIR / "gate_tuning_dev.json"
    gate_tune_dev = None
    if gate_tune_path.exists():
        with open(gate_tune_path, "r", encoding="utf-8") as f:
            gate_tune_dev = json.load(f)

    # 3. Đọc pipeline_union_summary_{tag}.json từ chạy thực tế
    dev_summary_path = RESULTS_DIR / "pipeline_union_summary_dev.json"
    locked_summary_path = RESULTS_DIR / "pipeline_union_summary_locked.json"

    dev_summary = None
    if dev_summary_path.exists():
        with open(dev_summary_path, "r", encoding="utf-8") as f:
            dev_summary = json.load(f)

    locked_summary = None
    if locked_summary_path.exists():
        with open(locked_summary_path, "r", encoding="utf-8") as f:
            locked_summary = json.load(f)

    # 4. Đọc kết quả ablation study
    ablation_path = RESULTS_DIR / "ablation_study_locked.json"
    ablation_data = None
    if ablation_path.exists():
        with open(ablation_path, "r", encoding="utf-8") as f:
            ablation_data = json.load(f)

    metrics_runtime = {
        "title": "Runtime, Refusal, Gate & Ablation Benchmark (R2, R3)",
        "gate_configuration_active": gate_cfg,
        "gate_tuning_dev_result": gate_tune_dev,
        "refusal_pipeline_eval": {
            "dev_set": dev_summary if dev_summary else {
                "status": "Chưa có pipeline_union_summary_dev.json",
                "note": "Cần chạy: python -m backend.eval.pipeline_union_eval --csv backend/data/test/dev_questions.csv --tag dev",
            },
            "locked_set": locked_summary if locked_summary else {
                "status": "Chưa có pipeline_union_summary_locked.json",
                "note": "Cần chạy: python -m backend.eval.pipeline_union_eval --csv backend/data/test/test_questions_locked.csv --tag locked",
            },
        },
        "ablation_study_locked": ablation_data if ablation_data else {
            "status": "Chưa chạy run_ablation_eval.py",
        },
        "runtime_latency_benchmarks": {
            "status": "bỏ claim số cứng micro-benchmarks",
            "reason": "Chưa thực hiện đo đạc benchmark latency cô lập (isolated micro-benchmark) với P95/P99 theo giao thức chuẩn. Không đưa ra số liệu suy đoán.",
            "note": "Thời gian phản hồi Gemini API và FAISS/BM25 phụ thuộc tải mạng và I/O; thời gian end-to-end được ghi nhận qua cột latency_ms.",
        },
        "disclaimed_unmeasured_claims": [
            "BGE-M3 vs bkai benchmark (bỏ claim do xung đột chiều 1024 vs 768)",
            "Đánh giá của con người theo thang điểm Likert 5 mức (bỏ claim do chưa tổ chức thử nghiệm người dùng diện rộng)",
            "100% Attribution Precision tuyệt đối trên mọi kịch bản ngoại biên (Attribution gate chặn hallucination chunk_id, nhưng cần context thực tế)",
        ],
    }

    out_file = RESULTS_DIR / "metrics_runtime.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(metrics_runtime, f, indent=2, ensure_ascii=False)
    print(f"Đã xuất: {out_file}")


if __name__ == "__main__":
    compile_retrieval_metrics()
    compile_runtime_metrics()
