"""
audit_gold_chunks.py — Kiểm tra và đối chiếu gold chunk IDs với Index FAISS/BM25 thực tế.

Giải quyết triệt để Feedback #2 của Giảng viên:
  "Gold chunk không có trong index: 35/393 câu có gold (22 chunk ID khác nhau, khoảng 8,9%)
   trỏ tới chunk không tồn tại trong faiss_meta.jsonl đã commit; báo cáo chỉ nêu 9 câu và 4 ID.
   Recall và MRR bị chặn trên một cách nhân tạo."

Script này:
  1. Đọc faiss_meta.jsonl để lấy tập hợp chunk_id hợp lệ (725 chunks).
  2. Đối chiếu toàn bộ câu hỏi trong dataset (dev hoặc locked).
  3. Phân loại:
     - In-scope / Year-control có chunk hợp lệ trong index
     - In-scope / Year-control có chunk KHÔNG tồn tại trong index
     - Out-of-scope (không cần chunk retrieval)
  4. Cung cấp ánh xạ chuẩn xác (canonical mapping) cho các ID lỗi lịch sử (ví dụ _r000 thay vì số dòng thực tế).
  5. Xuất báo cáo Markdown và JSON để minh bạch hóa hoàn toàn mẫu hiệu lực.
"""

import json
import csv
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
INDEX_META_PATH = PROJECT_ROOT / "backend" / "data" / "index" / "faiss_meta.jsonl"

# Ánh xạ đã được xác thực ngữ nghĩa và số liệu cho các lỗi gán nhãn lịch sử
CANONICAL_REPLACEMENTS = {
    # Cơ sở Vũng Tàu (Nguyễn Văn Thư)
    ("thong_tin_chung_2026_co-so_chunks", "Vũng Tàu"): "2026_diem-chuan_dai-hoc-chinh-quy_s065",
    # 2025 bảng điểm chuẩn - r000 là placeholder lỗi khi trích xuất bảng
    ("2025_diem-chuan_dai-hoc-chinh-quy_t000_r000", "7220201A"): "2025_diem-chuan_dai-hoc-chinh-quy_t000_r002",  # Ngôn ngữ Anh
    ("2025_diem-chuan_dai-hoc-chinh-quy_t000_r000", "748020101A"): "2025_diem-chuan_dai-hoc-chinh-quy_t000_r013", # CNTT
    ("2025_diem-chuan_dai-hoc-chinh-quy_t000_r000", "7520216A"): "2025_diem-chuan_dai-hoc-chinh-quy_t001_r007",  # KT Điều khiển
    ("2025_diem-chuan_dai-hoc-chinh-quy_t000_r000", "7340101A"): "2025_diem-chuan_dai-hoc-chinh-quy_t000_r005",  # Quản trị KD
    # 2024 bảng điểm chuẩn
    ("2024_diem-chuan_dai-hoc-chinh-quy_t000_r000", "7480102A"): "2024_diem-chuan_dai-hoc-chinh-quy_t000_r006",  # Mạng máy tính
    ("2024_diem-chuan_dai-hoc-chinh-quy_t000_r000", "7510205A"): "2024_diem-chuan_dai-hoc-chinh-quy_t000_r014",  # CNKT Ô tô
    ("2024_diem-chuan_dai-hoc-chinh-quy_t000_r000", "784010402A"): "2024_diem-chuan_dai-hoc-chinh-quy_t000_r034",# Kinh tế vận tải HK
    # 2023 điểm chuẩn
    ("2023_diem-chuan_dai-hoc-chinh-quy_t000_r000", "25.65"): "2023_diem-chuan_dai-hoc-chinh-quy_txt_s001",       # Logistics CLC 25.65
}


def load_valid_index_chunks(meta_path: Path) -> set[str]:
    valid_ids = set()
    with open(meta_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                data = json.loads(line)
                valid_ids.add(data["chunk_id"])
    return valid_ids


def audit_dataset(dataset_path: Path, index_chunks: set[str]) -> Dict[str, Any]:
    with open(dataset_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    total_count = len(rows)
    valid_gold_rows = []
    missing_gold_rows = []
    oos_rows = []
    mapped_corrections = []

    for r in rows:
        qid = int(r["id"]) if r.get("id") else None
        cat = r.get("category", "").strip()
        behavior = r.get("expected_behavior", "").strip()
        query = r.get("user_query", "").strip()
        cid = r.get("chunk_id", "").strip()
        fact = r.get("core_fact", "").strip()

        if behavior == "refuse" or cat == "out_of_scope":
            oos_rows.append({
                "id": qid,
                "category": cat,
                "query": query,
                "chunk_id": cid
            })
            continue

        if not cid:
            missing_gold_rows.append({
                "id": qid,
                "category": cat,
                "query": query,
                "chunk_id": "<EMPTY>",
                "reason": "Missing chunk_id in in-scope question",
                "core_fact": fact
            })
            continue

        if cid in index_chunks:
            valid_gold_rows.append({
                "id": qid,
                "category": cat,
                "query": query,
                "chunk_id": cid
            })
        else:
            # Check for known replacement
            mapped_cid = None
            for (bad_cid, token), good_cid in CANONICAL_REPLACEMENTS.items():
                if cid == bad_cid and (token in fact or token in query):
                    mapped_cid = good_cid
                    break

            missing_gold_rows.append({
                "id": qid,
                "category": cat,
                "query": query,
                "chunk_id": cid,
                "reason": "Chunk ID not found in canonical index",
                "suggested_canonical_chunk": mapped_cid,
                "core_fact": fact
            })
            if mapped_cid:
                mapped_corrections.append({
                    "id": qid,
                    "query": query,
                    "old_chunk_id": cid,
                    "mapped_chunk_id": mapped_cid
                })

    missing_cids = sorted(list({r["chunk_id"] for r in missing_gold_rows}))
    in_scope_total = len(valid_gold_rows) + len(missing_gold_rows)

    return {
        "dataset_name": dataset_path.name,
        "total_questions": total_count,
        "in_scope_questions": in_scope_total,
        "out_of_scope_questions": len(oos_rows),
        "valid_gold_count": len(valid_gold_rows),
        "missing_gold_count": len(missing_gold_rows),
        "missing_gold_percentage": round(len(missing_gold_rows) / in_scope_total * 100, 2) if in_scope_total else 0,
        "unique_missing_chunk_ids": missing_cids,
        "unique_missing_chunk_count": len(missing_cids),
        "mapped_corrections_count": len(mapped_corrections),
        "missing_details": missing_gold_rows,
        "mapped_details": mapped_corrections
    }


def generate_markdown_report(audit_result: Dict[str, Any], output_path: Path):
    res = audit_result
    lines = [
        f"# Báo cáo Đối chiếu Gold Chunk với Index Canonical — {res['dataset_name']}",
        "",
        "> [!IMPORTANT]",
        f"**Tổng kết kiểm toán:**",
        f"- Tổng số câu hỏi: `{res['total_questions']}`",
        f"- Số câu hỏi cần Retrieval (In-scope + Year-control): `{res['in_scope_questions']}`",
        f"- Số câu hỏi Out-of-scope (Không cần Retrieval, chỉ đo Refusal): `{res['out_of_scope_questions']}`",
        f"- Số câu có Gold Chunk tồn tại trong Index (Valid): `{res['valid_gold_count']}` ({100 - res['missing_gold_percentage']:.2f}%)",
        f"- Số câu có Gold Chunk KHÔNG tồn tại trong Index (Missing): `{res['missing_gold_count']}` ({res['missing_gold_percentage']}%)",
        f"- Số Chunk ID độc nhất bị thiếu: `{res['unique_missing_chunk_count']}`",
        f"- Số câu có thể ánh xạ tự động sang chunk chuẩn (Canonical mapping): `{res['mapped_corrections_count']}`",
        "",
        "## 1. Danh sách Chunk ID không tồn tại trong Index",
        ""
    ]

    for cid in res["unique_missing_chunk_ids"]:
        count = sum(1 for r in res["missing_details"] if r["chunk_id"] == cid)
        lines.append(f"- `{cid}`: xuất hiện ở {count} câu hỏi.")

    lines.extend([
        "",
        "## 2. Chi tiết các câu hỏi bị lệch Gold Chunk & Ánh xạ khắc phục",
        "",
        "| ID | Nhóm | Chunk ID cũ | Chunk ID chuẩn hóa | Câu hỏi |",
        "|---|---|---|---|---|"
    ])

    for r in res["missing_details"]:
        sug = r.get("suggested_canonical_chunk") or "*Chưa ánh xạ*"
        q_short = r["query"][:60].replace("|", "/")
        lines.append(f"| {r['id']} | {r['category']} | `{r['chunk_id']}` | `{sug}` | {q_short} |")

    lines.extend([
        "",
        "## 3. Khuyến nghị cho Đánh giá Retrieval (Chapter 5)",
        "",
        "Để khắc phục trọn vẹn phản hồi của Giảng viên về việc MRR/Recall bị chặn trên nhân tạo:",
        "1. **Protocol A (Raw):** Chạy đánh giá trên toàn bộ tập câu hỏi in-scope với Gold gốc. Báo cáo rõ trần Recall bị giảm do missing chunk.",
        "2. **Protocol B (Valid Subset):** Báo cáo metric trên tập câu hỏi hợp lệ (`N = {res['valid_gold_count']}`) để đánh giá chính xác năng lực retriever.",
        "3. **Protocol C (Canonical Mapped):** Ánh xạ các chunk `_r000` về dòng dữ liệu thực tế và tính toán lại toàn bộ Bảng 5.1.",
        ""
    ])

    output_path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Audit gold chunks against index")
    parser.add_argument("--dataset", type=str, default="backend/data/test/test_questions_locked.csv")
    args = parser.parse_args()

    ds_path = PROJECT_ROOT / args.dataset
    if not ds_path.exists():
        print(f"File not found: {ds_path}")
        return

    index_chunks = load_valid_index_chunks(INDEX_META_PATH)
    print(f"Đã nạp {len(index_chunks)} chunks từ index canonical.")

    res = audit_dataset(ds_path, index_chunks)

    out_dir = PROJECT_ROOT / "backend" / "eval" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)

    json_path = out_dir / f"audit_{ds_path.stem}.json"
    md_path = out_dir / f"audit_{ds_path.stem}.md"

    json_path.write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    generate_markdown_report(res, md_path)

    print(f"Audit hoàn tất cho {ds_path.name}:")
    print(f"  Valid gold rows: {res['valid_gold_count']}/{res['in_scope_questions']}")
    print(f"  Missing gold rows: {res['missing_gold_count']}")
    print(f"  Mapped replacements: {res['mapped_corrections_count']}")
    print(f"  Báo cáo: {md_path}")


if __name__ == "__main__":
    main()
