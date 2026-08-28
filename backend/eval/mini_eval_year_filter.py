"""
mini_eval_year_filter.py — Đánh giá nhanh year_filter.py trên test_questions.csv

Đo:
  - Accuracy phân loại document_type (spot-check ~50 câu)
  - False positive của bộ keyword out-of-scope (câu in-scope bị chặn nhầm)

Usage:
    python backend/eval/mini_eval_year_filter.py
"""

import csv
import os
import sys
from collections import Counter

# Allow import from app/services when running from backend/
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

from app.services.year_filter import analyze, FilterResult

TEST_CSV = os.path.join(BACKEND_DIR, "data", "test", "test_questions.csv")


def load_questions(path: str):
    questions = []
    with open(path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            questions.append(row)
    return questions


def main():
    if not os.path.exists(TEST_CSV):
        print(f"[ERROR] Không tìm thấy {TEST_CSV}")
        sys.exit(1)

    questions = load_questions(TEST_CSV)
    print(f"Tổng số câu hỏi: {len(questions)}")

    # ------------------------------------------------------------------
    # Phần A: False positive của keyword out-of-scope
    # ------------------------------------------------------------------
    fp_in_scope = []
    correct_refuse = []
    refused_oos = []
    for q in questions:
        query = q["user_query"]
        category = q["category"].strip()
        expected = q["expected_behavior"].strip()
        result = analyze(query)

        if expected == "refuse":
            if result.status == "refused" and result.code == "OUT_OF_SCOPE":
                correct_refuse.append(query)

        if category == "in_scope":
            # in-scope không được bị chặn bởi keyword out-of-scope
            if result.status == "refused" and result.code == "OUT_OF_SCOPE":
                fp_in_scope.append((query, result.refusal_source))

        if expected == "refuse" and result.status == "refused" and result.code == "OUT_OF_SCOPE":
            refused_oos.append(query)

    oos_total = sum(1 for q in questions if q["expected_behavior"].strip() == "refuse")
    in_scope_total = sum(1 for q in questions if q["category"].strip() == "in_scope")

    print("\n" + "=" * 60)
    print("PHẦN A — Keyword out-of-scope evaluation")
    print("=" * 60)
    print(f"Câu out_of_scope (expected=refuse): {oos_total}")
    print(f"Câu in_scope: {in_scope_total}")
    print(f"Out-of-scope bị chặn đúng (OUT_OF_SCOPE): {len(correct_refuse)}/{oos_total}")
    print(f"Câu in_scope bị chặn nhầm (false positive): {len(fp_in_scope)}")
    if fp_in_scope:
        print("\n👉 FALSE POSITIVES (cần sửa):")
        for q, src in fp_in_scope:
            print(f"  - [{src}] {q}")
    if in_scope_total > 0:
        fp_rate = len(fp_in_scope) / in_scope_total * 100
        print(f"\nFalse positive rate: {fp_rate:.2f}% (mục tiêu < 5%)")

    # ------------------------------------------------------------------
    # Phần B: Spot-check document_type trên 50 câu in_scope đầu tiên
    # ------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("PHẦN B — Spot-check document_type (50 câu đầu in_scope)")
    print("=" * 60)
    sample_inscope = [q for q in questions if q["category"].strip() == "in_scope"][:50]
    doc_counter = Counter()
    for q in sample_inscope:
        result = analyze(q["user_query"])
        dt = result.document_type or "None"
        doc_counter[dt] += 1

    for dt, cnt in doc_counter.most_common():
        print(f"  {str(dt):<25} {cnt}")

    # ------------------------------------------------------------------
    # Tổng kết
    # ------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("TỔNG KẾT")
    print("=" * 60)
    oos_pass = len(correct_refuse) / oos_total * 100 if oos_total else 0
    fp_pass = "✅ PASS" if (in_scope_total > 0 and fp_rate < 5) else ("ℹ️ CHƯA ĐÁNH GIÁ" if in_scope_total == 0 else "❌ FAIL")
    print(f"Refusal recall (out-of-scope chặn đúng): {oos_pass:.1f}%")
    print(f"False positive rate: {fp_pass}")


if __name__ == "__main__":
    main()
