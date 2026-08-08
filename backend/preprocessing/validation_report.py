"""
validation_report.py — Sinh báo cáo kiểm duyệt dữ liệu sau pipeline Bước 1–3.

Kiểm tra:
  - Số bảng trước/sau khi merge
  - Mỗi bảng có table_id và section_name hợp lệ chưa
  - Chất lượng OCR (chuỗi "i255", text toàn số)
  - Sample rows từ bảng đầu tiên để kiểm duyệt trực quan
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from utils import logger, load_json


# ---------------------------------------------------------------------------
# OCR quality helpers
# ---------------------------------------------------------------------------

_OCR_ERROR_PATTERNS = [
    re.compile(r"\bi255\b"),          # Glyph lookup failure → "i255"
    re.compile(r"^\d+(\s+\d+)+$"),   # String chỉ toàn số cách nhau bằng space
    re.compile(r"[^\x00-\x7F]{2,}.*[^\x00-\x7F]{2,}"),  # Quá nhiều non-ASCII liên tiếp
]


def is_ocr_error(text: str) -> bool:
    """Heuristic: returns True if the text looks like a garbled OCR artefact."""
    if not text or len(text.strip()) < 2:
        return False
    for pattern in _OCR_ERROR_PATTERNS:
        if pattern.search(text.strip()):
            return True
    return False


def count_ocr_errors(doc_dict: dict) -> int:
    """Counts text nodes that appear to be OCR errors."""
    count = 0
    for text in doc_dict.get("docling_output", {}).get("texts", []):
        t = text.get("text", "")
        if is_ocr_error(t):
            count += 1
    return count


# ---------------------------------------------------------------------------
# Table quality helpers
# ---------------------------------------------------------------------------

def extract_sample_rows(table: dict, max_rows: int = 3) -> List[List[str]]:
    """
    Extracts up to `max_rows` data rows (non-header) from a table as lists of cell texts.
    Rows are returned in row-index order, with cells sorted by column index.
    """
    cells = table.get("data", {}).get("table_cells", [])
    # Group non-header cells by row index
    data_cells = [c for c in cells if not c.get("column_header", False)]
    row_map: Dict[int, List[dict]] = {}
    for cell in data_cells:
        r = cell.get("start_row_offset_idx", 0)
        row_map.setdefault(r, []).append(cell)

    rows = []
    for r_idx in sorted(row_map.keys())[:max_rows]:
        row_cells = sorted(row_map[r_idx], key=lambda c: c.get("start_col_offset_idx", 0))
        rows.append([c.get("text", "").strip() for c in row_cells])
    return rows


def extract_header_row(table: dict) -> List[str]:
    """Extracts column header texts in column order."""
    cells = table.get("data", {}).get("table_cells", [])
    header_cells = [c for c in cells if c.get("column_header", False)]
    if not header_cells:
        return []
    # Get header row with the smallest row index
    min_row = min(c.get("start_row_offset_idx", 0) for c in header_cells)
    top_header = [c for c in header_cells if c.get("start_row_offset_idx") == min_row]
    top_header.sort(key=lambda c: c.get("start_col_offset_idx", 0))
    return [c.get("text", "").strip() for c in top_header]


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def calculate_vn_ratio(doc_dict: dict) -> float:
    """Calculates the ratio of Vietnamese diacritic characters over all alphabetic characters."""
    texts = doc_dict.get("docling_output", {}).get("texts", [])
    all_text = ""
    for text_node in texts:
        all_text += text_node.get("text", "")
        
    letters = [c for c in all_text if c.isalpha()]
    if not letters:
        return 0.0
        
    # Vietnamese-specific diacritic characters
    vn_special_chars = "ăâđêôơưáàảãạấầẩẫậắằẳẵặéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵĂÂĐÊÔƠƯ"
    vn_count = sum(1 for c in letters if c in vn_special_chars)
    return vn_count / len(letters)


def generate_validation_report(
    raw_dir: str = "backend/data/raw",
    docling_dir: str = "backend/data/processed/docling",
    section_dir: str = "backend/data/processed/section",
    report_output_path: str = "data_validation_report.md",
):
    """
    Analyzes the outputs of the preprocessing pipeline (Bước 1–3) and
    generates a detailed Markdown Data Validation Report.
    """
    logger.info("Generating Data Validation Report...")

    docling_path = Path(docling_dir)
    section_path = Path(section_dir)

    if not section_path.exists():
        logger.error(f"Section directory does not exist: {section_dir}")
        return

    processed_files = sorted(section_path.glob("*.json"))
    if not processed_files:
        logger.warning(f"No JSON files found in {section_dir} — pipeline may not have run yet.")
        return

    total_docs = len(processed_files)
    total_raw_tables = 0
    total_merged_tables = 0
    total_merged_events = 0
    total_unassigned = 0
    total_ocr_errors = 0

    documents_stats = []

    for file in processed_files:
        doc = load_json(str(file))
        if not doc:
            continue

        file_meta = doc.get("file_metadata", {})
        docling_out = doc.get("docling_output", {})
        meta_pre = doc.get("metadata_preprocessed", {})

        # Count raw tables (before merge) from docling output
        step1_file = docling_path / file.name
        raw_tables_count = 0
        raw_ocr_errors = 0
        if step1_file.exists():
            step1_doc = load_json(str(step1_file))
            if step1_doc:
                raw_tables_count = len(step1_doc.get("docling_output", {}).get("tables", []))
                raw_ocr_errors = count_ocr_errors(step1_doc)

        merged_tables = docling_out.get("tables", [])
        merged_count = meta_pre.get("tables_merged_count", 0)

        # Calculate Vietnamese diacritics ratio
        vn_ratio = calculate_vn_ratio(doc)

        # Check section assignment quality
        unassigned = [
            t for t in merged_tables
            if not t.get("section_name") or t.get("section_name") == "Unknown Section"
        ]

        total_raw_tables += raw_tables_count
        total_merged_tables += len(merged_tables)
        total_merged_events += merged_count
        total_unassigned += len(unassigned)
        total_ocr_errors += raw_ocr_errors

        # Build per-table detail
        table_details = []
        for t in merged_tables:
            cells = t.get("data", {}).get("table_cells", [])
            num_cols = max((c.get("end_col_offset_idx", 0) for c in cells), default=0)
            num_rows = max((c.get("end_row_offset_idx", 0) for c in cells), default=0)
            prov = t.get("prov", [])
            page_no = prov[0].get("page_no", "?") if prov else "?"
            pages = t.get("_merged_from_pages") or [page_no]
            section = t.get("section_name") or "⚠️ Unknown"
            header = extract_header_row(t)
            samples = extract_sample_rows(t, max_rows=2)
            table_details.append({
                "table_id": t.get("table_id", "?"),
                "rows": num_rows,
                "cols": num_cols,
                "section": section,
                "pages": pages,
                "header": header,
                "samples": samples,
                "merged": t.get("_merged", False),
            })

        documents_stats.append({
            "name": file_meta.get("file_name", file.name),
            "program_type": file_meta.get("program_type", "?"),
            "year": file_meta.get("admission_year"),
            "raw_tables": raw_tables_count,
            "merged_tables": len(merged_tables),
            "merged_events": merged_count,
            "unassigned": len(unassigned),
            "ocr_errors": raw_ocr_errors,
            "vn_ratio": vn_ratio,
            "table_details": table_details,
        })

    # -----------------------------------------------------------------------
    # Write Markdown Report
    # -----------------------------------------------------------------------
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = []

    lines.append("# Báo Cáo Kiểm Duyệt Dữ Liệu — Pipeline Bước 1–3")
    lines.append(f"\n*Sinh tự động lúc: {now}*\n")

    # --- Executive Summary ---
    lines.append("## 1. Tóm Tắt Tổng Quan\n")
    lines.append("| Chỉ số | Giá trị |")
    lines.append("| :--- | ---: |")
    lines.append(f"| Tổng tài liệu đã xử lý | **{total_docs}** |")
    lines.append(f"| Tổng bảng (raw từ Docling) | {total_raw_tables} |")
    lines.append(f"| Tổng bảng (sau merge) | **{total_merged_tables}** |")
    lines.append(f"| Số lần merge thực hiện | {total_merged_events} |")
    lines.append(f"| Bảng chưa được gán mục (Unknown Section) | {'✅ 0' if total_unassigned == 0 else f'⚠️ {total_unassigned}'} |")
    lines.append(f"| Text nodes bị lỗi OCR (ước tính) | {'✅ Thấp' if total_ocr_errors < 20 else f'⚠️ {total_ocr_errors}'} |")
    
    # Thêm kiểm tra tỷ lệ tiếng Việt mất dấu
    low_vn_files = [d for d in documents_stats if d["vn_ratio"] < 0.05]
    if low_vn_files:
        lines.append(f"| Cảnh báo mất dấu tiếng Việt | ⚠️ Phát hiện {len(low_vn_files)} file có tỷ lệ dấu rất thấp (< 5%) |")
    else:
        lines.append(f"| Cảnh báo mất dấu tiếng Việt | ✅ Tất cả các file đều giữ dấu tốt |")
        
    lines.append("")

    # --- Per-document detail ---
    lines.append("## 2. Chi Tiết Theo Tài Liệu\n")

    for doc in documents_stats:
        year_str = str(doc["year"]) if doc["year"] else "N/A"
        lines.append(f"### {doc['name']}")
        lines.append(f"- **Hệ đào tạo:** `{doc['program_type']}`")
        lines.append(f"- **Năm:** `{year_str}`")
        lines.append(f"- **Tỷ lệ ký tự có dấu tiếng Việt:** `{doc['vn_ratio']:.2%}`")
        lines.append(f"- **Bảng (raw / sau merge):** `{doc['raw_tables']}` → `{doc['merged_tables']}`  (merged {doc['merged_events']} lần)")
        lines.append(f"- **Bảng Unknown Section:** `{doc['unassigned']}`")
        lines.append(f"- **OCR errors ước tính:** `{doc['ocr_errors']}` text nodes")
        lines.append("")

        if doc["table_details"]:
            lines.append("| ID | Trang | Rows | Cols | Merged? | Mục ngữ nghĩa |")
            lines.append("| :--- | :---: | :---: | :---: | :---: | :--- |")
            for t in doc["table_details"]:
                pages_str = ", ".join(str(p) for p in t["pages"])
                merged_str = "✅ Yes" if t["merged"] else "No"
                section_str = t["section"] if t["section"] != "Unknown Section" else "⚠️ Unknown"
                lines.append(
                    f"| {t['table_id']} | {pages_str} | {t['rows']} | {t['cols']} | {merged_str} | {section_str} |"
                )
            lines.append("")

            # Sample data for first table
            first = doc["table_details"][0]
            if first["header"] or first["samples"]:
                lines.append(f"**Mẫu dữ liệu — {first['table_id']} (section: {first['section']}):**")
                lines.append("")
                if first["header"]:
                    cols = " | ".join(first["header"])
                    sep = " | ".join(["---"] * len(first["header"]))
                    lines.append(f"| {cols} |")
                    lines.append(f"| {sep} |")
                for row in first["samples"]:
                    lines.append(f"| {' | '.join(row)} |")
                lines.append("")
        else:
            lines.append("*(Tài liệu này không chứa bảng biểu)*\n")

    # --- Quality Assessment ---
    lines.append("## 3. Đánh Giá Chất Lượng\n")

    if total_unassigned == 0:
        lines.append("> [!NOTE]")
        lines.append("> **Section Assignment:** Tất cả bảng đã được gán mục ngữ nghĩa hợp lệ ✅")
    else:
        lines.append("> [!WARNING]")
        lines.append(f"> **Section Assignment:** Còn {total_unassigned} bảng chưa được gán mục (Unknown Section). Cần kiểm tra section_assignment.py.")

    lines.append("")

    if total_merged_events > 0:
        lines.append("> [!NOTE]")
        lines.append(f"> **Table Merge:** Đã ghép {total_merged_events} cặp bảng bị cắt qua trang ✅")
    else:
        lines.append("> [!NOTE]")
        lines.append("> **Table Merge:** Không có bảng nào bị cắt qua trang (tables_merged_count = 0). Đây có thể là bình thường nếu PDF không có bảng trải qua nhiều trang.")

    lines.append("")

    if total_ocr_errors > 50:
        lines.append("> [!WARNING]")
        lines.append(
            f"> **OCR Quality:** Phát hiện ~{total_ocr_errors} text nodes có dấu hiệu lỗi encoding "
            "(chuỗi 'i255', toàn số). Đây thường xuất hiện ở trang bìa/header — "
            "không ảnh hưởng đến dữ liệu bảng chính nếu table_cells trích đúng."
        )
    else:
        lines.append("> [!NOTE]")
        lines.append("> **OCR Quality:** Số text nodes lỗi OCR ở mức thấp/chấp nhận được ✅")

    lines.append("")

    # Đánh giá tỷ lệ mất dấu
    if low_vn_files:
        lines.append("> [!WARNING]")
        lines.append(
            f"> **Vietnamese Diacritics:** Phát hiện {len(low_vn_files)} file có tỷ lệ ký tự có dấu rất thấp. "
            "Điều này cho thấy OCR có thể đang dùng sai engine tiếng Việt hoặc text layer bị hỏng CMap. "
            "Vui lòng kiểm tra lại cấu hình `--ocr-engine`."
        )
    else:
        lines.append("> [!NOTE]")
        lines.append("> **Vietnamese Diacritics:** Tất cả tài liệu đều giữ được tỷ lệ ký tự có dấu tiếng Việt chuẩn xác ✅")

    # Save report
    try:
        with open(report_output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        logger.info(f"Validation report written to: {report_output_path}")
    except Exception as e:
        logger.error(f"Failed to write report: {e}")


if __name__ == "__main__":
    generate_validation_report()
