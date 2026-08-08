"""
Bước 5 — Paste-down + Segment Context

Input : backend/data/processed/footnotes/*.json
Output: backend/data/processed/pastedown/*.json

Chức năng:
1. Paste-down merge dọc (row_span > 1): lan giá trị ô chứa xuống các dòng
   bên dưới trong cùng cột (chỉ dòng data, không lan ô header).
   - Cần cho các file 2022-2025 có nhóm merge dọc.
   - File 2026 chính quy: pass-through (không có row_span > 1).
2. Segment context: gắn `segment_context` cho mỗi bảng suy từ section_name
   (vd campus BÀ RỊA VŨNG TÀU, chương trình chuẩn/tiên tiến, liên kết 2+2).
"""
import re
from pathlib import Path
from typing import Dict, List, Optional

from utils import logger, save_json, load_json

# Pattern suy segment từ section_name
SEGMENT_RULES = [
    (re.compile(r"BÀ RỊA|VŨNG TÀU|VUNG TAU", re.IGNORECASE), "Campus: Bà Rịa - Vũng Tàu"),
    (re.compile(r"liên kết đào tạo với nước ngoài|liên kết quốc tế|2\+2", re.IGNORECASE), "Chương trình liên kết quốc tế (2+2)"),
    (re.compile(r"chương trình tiên tiến", re.IGNORECASE), "Chương trình tiên tiến"),
    (re.compile(r"hoàn toàn bằng tiếng anh|hoàn toàn bằng anh", re.IGNORECASE), "Chương trình hoàn toàn bằng Tiếng Anh"),
]


def infer_segment(section_name: str) -> Optional[str]:
    """Suy segment context từ section_name."""
    if not section_name or section_name == "Unknown Section":
        return None
    for pattern, label in SEGMENT_RULES:
        if pattern.search(section_name):
            return label
    return None


def paste_down_cells(table: dict) -> None:
    """
    Lan giá trị ô row_span>1 xuống các dòng data bên dưới.
    Cách làm: với mỗi ô có row_span>1, tạo bản sao 'text_pasted' cho các
    dòng [start_row+1 .. end_row] trong cùng cột (nếu ô đó chưa có text).
    Ghi chú: docling đã đánh dấu row_span; các ô bên dưới thường là ô
    placeholder rỗng — nếu chúng có text khác rỗng thì KHÔNG ghi đè.
    """
    cells = table.get("data", {}).get("table_cells", [])
    # Nhóm cells theo (start_row, start_col) để tra cứu nhanh
    by_rc = {}
    for cell in cells:
        key = (cell.get("start_row_offset_idx", 0), cell.get("start_col_offset_idx", 0))
        by_rc[key] = cell

    pasted_count = 0
    for cell in cells:
        rs = cell.get("row_span", 1)
        if rs <= 1:
            continue
        r0 = cell.get("start_row_offset_idx", 0)
        c0 = cell.get("start_col_offset_idx", 0)
        src_text = (cell.get("text") or "").strip()
        if not src_text:
            continue
        for r in range(r0 + 1, r0 + rs):
            target = by_rc.get((r, c0))
            if target is None:
                continue
            t_text = (target.get("text") or "").strip()
            # Chỉ lan vào ô rỗng (điển hình của merge dọc)
            if not t_text:
                target["text"] = src_text
                target["text_pasted"] = True
                target["pasted_from"] = f"r{r0}c{c0}"
                pasted_count += 1
    logger.debug(f"  paste_down: {pasted_count} cells filled from row_span.")


def add_segment_context(doc_dict: dict) -> dict:
    """Gắn segment_context cho từng bảng."""
    for table in doc_dict.get("docling_output", {}).get("tables", []):
        section = table.get("section_name", "")
        seg = infer_segment(section)
        table["segment_context"] = seg
        if seg:
            logger.debug(f"  {table.get('table_id')} -> segment: {seg}")
    return doc_dict


def process_all_documents(
    input_dir: str = "backend/data/processed/footnotes",
    output_dir: str = "backend/data/processed/pastedown",
    target_stem: Optional[str] = None,
):
    """Chạy paste-down + segment context."""
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    json_files = list(input_path.glob("*.json"))
    if target_stem:
        json_files = [f for f in json_files if target_stem in f.name]
        logger.info(f"Single-file mode: targeting '{target_stem}', found {len(json_files)} file(s).")
    else:
        logger.info(f"Found {len(json_files)} footnote-resolved documents.")

    for file in json_files:
        logger.info(f"Processing: {file.name}")
        doc_dict = load_json(str(file))
        if not doc_dict:
            continue
        for table in doc_dict.get("docling_output", {}).get("tables", []):
            paste_down_cells(table)
        add_segment_context(doc_dict)
        # Ghi nhận bước đã chạy
        doc_dict.setdefault("metadata_preprocessed", {})["pipeline_step_5_paste_down"] = True
        dest_path = output_path / file.name
        save_json(doc_dict, str(dest_path))


if __name__ == "__main__":
    process_all_documents()
