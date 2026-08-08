"""
Bước 6 — Row-level KV Chunking (cốt lõi)

Input : backend/data/processed/pastedown/*.json
Output: backend/data/processed/chunks/*.json (data) + spot_check_report.md

Mỗi dòng dữ liệu của bảng -> 1 chunk tự chứa, bảo toàn header path,
LLM-readable, retrievable.

Quyết định đã chốt:
- Whitelist 2 lớp cho mã xét tuyển (apply_digit_rule -> match whitelist -> auto-accept)
- JSON là single source of truth (export_derived.py sinh JSONL/MD/TXT từ đây)
- Header template chuẩn cho bảng continuation (cắt qua trang, mất header khi merge)
"""
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from utils import logger, save_json, load_json

# ---------------------------------------------------------------------------
# Hằng số
# ---------------------------------------------------------------------------

WHITELIST_PATH = Path("backend/data/whitelist_codes.json")
SOURCE_URLS_PATH = Path("backend/data/source_urls.json")

# Chuẩn hoá header/section bị OCR đọc nhầm (/ -> I, đảo từ)
HEADER_FIX_RULES = [
    (re.compile(r"NGÀNHICHUYÊN NGÀNH", re.IGNORECASE), "NGÀNH/CHUYÊN NGÀNH"),
    (re.compile(r"NgànhIChuyên ngành đào tạo"), "Ngành/Chuyên ngành đào tạo"),
    (re.compile(r"NgànhIChuyên ngành"), "Ngành/Chuyên ngành"),
    (re.compile(r"NgànhI"), "Ngành/"),
    (re.compile(r"Tổ môn xét tuyển hợp"), "Tổ hợp môn xét tuyển"),
]

# Template header chuẩn theo số cột — dùng khi bảng continuation bị mất header
# (bảng cắt qua trang được tách bởi merge_tables, hoặc OCR không nhận diện header)
HEADER_TEMPLATES = {
    5: ["STT", "Mã xét tuyển", "Ngành/Chuyên ngành đào tạo", "Môn bắt buộc", "Môn tự chọn"],
    6: ["STT", "Mã xét tuyển", "Ngành/Chuyên ngành đào tạo", "Tổ hợp môn xét tuyển", "Chỉ tiêu", "Ghi chú"],
}

# Rule digit cho mã: 2 chữ số ở vị trí index 6,7 của chuỗi "UTH"+3 ký tự+2 số+suf
DIGIT_MAP = {"O": "0", "I": "1", "S": "5", "Z": "2"}


# ---------------------------------------------------------------------------
# Tiện ích
# ---------------------------------------------------------------------------

def load_whitelist() -> Dict[str, List[str]]:
    data = load_json(str(WHITELIST_PATH))
    if not data:
        logger.error("Cannot load whitelist_codes.json — abort.")
        raise SystemExit(1)
    return data


def load_source_urls() -> Dict[str, dict]:
    """Load source URL mapping từ source_urls.json."""
    data = load_json(str(SOURCE_URLS_PATH))
    if not data:
        logger.warning("Cannot load source_urls.json — source_urls sẽ để trống.")
        return {}
    return data


def apply_digit_rule(code: str) -> Tuple[str, bool]:
    """Apply O->0, I->1, S->5, Z->2 tại đúng 2 vị trí chữ số."""
    if len(code) != 9:
        return code, False
    base = code[:3]
    grp = code[3:6]
    dig = code[6:8]
    suf = code[8:9]
    corr = ""
    changed = False
    for ch in dig:
        corr += DIGIT_MAP.get(ch, ch)
        if ch in DIGIT_MAP:
            changed = True
    return base + grp + corr + suf, changed


def classify_code(raw: str, whitelist: Dict[str, List[str]]) -> Dict[str, object]:
    """Whitelist 2 lớp: apply_digit_rule -> match standard/ambiguous."""
    candidate, changed = apply_digit_rule(raw)
    standard = set(whitelist.get("standard", []))
    ambiguous = set(whitelist.get("ambiguous", []))

    if candidate in standard:
        return {
            "code_raw": raw,
            "code_corrected": candidate,
            "code_changed": changed,
            "code_needs_verification": False,
            "code_reason": "whitelist_match",
        }
    if candidate in ambiguous:
        return {
            "code_raw": raw,
            "code_corrected": candidate,
            "code_changed": changed,
            "code_needs_verification": True,
            "code_reason": "ambiguous_pattern",
        }
    return {
        "code_raw": raw,
        "code_corrected": candidate,
        "code_changed": changed,
        "code_needs_verification": True,
        "code_reason": "no_whitelist_match",
    }


def fix_header_text(text: str) -> str:
    """Sửa header/section bị OCR đọc nhầm."""
    for pattern, replacement in HEADER_FIX_RULES:
        text = pattern.sub(replacement, text)
    return text


# ---------------------------------------------------------------------------
# Detect header / build header path
# ---------------------------------------------------------------------------

def is_numeric_stt(text: str) -> bool:
    t = (text or "").strip()
    return bool(re.fullmatch(r"\d{1,3}", t))


# Header hints — CHỈ match text header thật, không match data
# (data chứa "chuyên ngành ..." nên KHÔNG đưa "chuyên ngành" vào hints)
HEADER_HINTS = [
    "stt", "mã xét tuyển", "mã ngành", "tên ngành",
    "môn bắt buộc", "môn tự chọn", "tổ hợp môn", "chỉ tiêu", "ghi chú",
]


def looks_like_header_text(text: str) -> bool:
    t = fix_header_text(text).strip().lower()
    if not t:
        return False
    for h in HEADER_HINTS:
        if h in t:
            return True
    return False


def row_is_data_with_stt(cells_in_row: List[dict]) -> bool:
    """Data row nếu STT là số nguyên (tăng dần hợp lệ)."""
    stt_cell = next((c for c in cells_in_row if c.get("start_col_offset_idx", 0) == 0), None)
    return stt_cell is not None and is_numeric_stt(stt_cell.get("text", ""))


def build_col_grid(cells: List[dict], num_cols: int) -> Dict[Tuple[int, int], dict]:
    grid = {}
    for c in cells:
        r = c.get("start_row_offset_idx", 0)
        c0 = c.get("start_col_offset_idx", 0)
        grid[(r, c0)] = c
    return grid


def template_header_paths(num_cols: int) -> Dict[int, str]:
    """Header template chuẩn cho bảng continuation (mất header khi merge/OCR)."""
    tmpl = HEADER_TEMPLATES.get(num_cols)
    paths: Dict[int, str] = {}
    for c in range(num_cols):
        if tmpl and c < len(tmpl):
            paths[c] = tmpl[c]
        else:
            paths[c] = f"Cột {c + 1}"
    return paths


def detect_header_rows(table: dict) -> Tuple[int, Dict[int, str]]:
    """
    Detect vùng header — KHÔNG dựa chủ yếu vào column_header (không tin):
    Duyệt từ row 0 xuống:
      - Row là DATA nếu cột STT (cột 0) có số nguyên liên tục.
      - Row là HEADER nếu có cell chứa text header đặc trưng (hints).
      - Nếu không tìm thấy header thật (bảng continuation / mất header):
        dùng HEADER_TEMPLATES theo num_cols, trả header_count=0 (data từ row 0).
    """
    cells = table.get("data", {}).get("table_cells", [])
    if not cells:
        return 0, {}

    max_row = max((c.get("start_row_offset_idx", 0) for c in cells), default=0)
    num_cols = table.get("data", {}).get("num_cols", 0)
    grid = build_col_grid(cells, num_cols)

    header_row_count = 0
    for r in range(0, max_row + 1):
        row_cells = [grid[(r, c)] for c in range(num_cols) if (r, c) in grid]
        if not row_cells:
            continue

        # 1) Data row: cột STT là số
        if row_is_data_with_stt(row_cells):
            break

        # 2) Header: có text đặc trưng
        has_hint = any(looks_like_header_text(c.get("text", "")) for c in row_cells)
        if has_hint:
            header_row_count += 1
            continue
        # Không phải data, không phải header -> dừng
        break

    # Không có header thật -> dùng template (bảng continuation)
    if header_row_count == 0:
        return 0, template_header_paths(num_cols)

    # Build full header path cho từng cột (nối nhiều tầng header, bỏ lặp span)
    col_header_path: Dict[int, str] = {}
    for c in range(num_cols):
        path_parts = []
        for r in range(header_row_count):
            cell = grid.get((r, c))
            if cell:
                t = fix_header_text((cell.get("text") or "").strip())
                if t and t not in path_parts:
                    path_parts.append(t)
        col_header_path[c] = " → ".join(path_parts) if path_parts else template_header_paths(num_cols)[c]

    return header_row_count, col_header_path


def build_cell_map(table: dict) -> Dict[Tuple[int, int], dict]:
    return build_col_grid(table.get("data", {}).get("table_cells", []), table.get("data", {}).get("num_cols", 0))


# ---------------------------------------------------------------------------
# Chunking chính
# ---------------------------------------------------------------------------

def get_cell_text(cell: Optional[dict]) -> str:
    if cell is None:
        return ""
    if cell.get("text_expanded"):
        return cell["text_expanded"].strip()
    return (cell.get("text") or "").strip()


def make_chunk_for_row(
    table: dict,
    row_idx: int,
    header_paths: Dict[int, str],
    grid: Dict[Tuple[int, int], dict],
    doc_meta: dict,
    whitelist: Dict[str, List[str]],
    tidx: int,
    source_urls_config: Dict[str, dict] = None,
) -> Optional[dict]:
    num_cols = table.get("data", {}).get("num_cols", 0)

    kv_parts: List[str] = []
    row_identifiers: Dict[str, str] = {}
    code_info: Optional[dict] = None
    has_any_text = False

    for c in range(num_cols):
        cell = grid.get((row_idx, c))
        if cell is None:
            continue
        text = get_cell_text(cell)
        if not text:
            continue
        has_any_text = True

        header = header_paths.get(c, f"Cột {c + 1}")
        header_lower = header.lower()

        # Cột mã xét tuyển — nhận diện bằng header hoặc pattern
        is_code_col = ("mã xét tuyển" in header_lower) or ("mã ngành" in header_lower) or bool(re.fullmatch(r"UTH[A-Z0-9]{5,6}", text))
        if is_code_col and re.fullmatch(r"UTH[A-Z0-9]{5,6}", text):
            code_info = classify_code(text, whitelist)
            kv_parts.append(f"{header}: {code_info['code_corrected']}")
            row_identifiers["ma_xtuyen"] = code_info["code_corrected"]
            row_identifiers["ma_xtuyen_raw"] = code_info["code_raw"]
            continue

        # Cột STT — không đưa vào text retrieval (giữ identifier)
        if header_lower in ("stt", "số tt", "stt.."):
            row_identifiers["stt"] = text
            continue

        # Cột ngành/chuyên ngành — lưu identifier
        if "ngành" in header_lower:
            row_identifiers["ten_nganh"] = text

        kv_parts.append(f"{header}: {text}")

    if not has_any_text:
        return None

    # --- Dựng chunk text ---
    section = fix_header_text(table.get("section_name", ""))
    seg = table.get("segment_context") or ""
    program_type = doc_meta.get("program_type", "")
    year = doc_meta.get("admission_year", "")

    prefix = f"[Năm {year} | Hệ {program_type} | {section}]"
    if seg:
        prefix += f" [{seg}]"

    body = ". ".join(kv_parts) + "."

    # Thêm annotation cấp bảng
    table_annotation = doc_meta.get("table_annotation_global") or ""
    if table_annotation:
        body = f"{body} {table_annotation}"

    # Thêm nguồn vào text để AI trích dẫn
    url_cfg = (source_urls_config or {}).get(program_type, {})
    all_source_urls = url_cfg.get("source_urls", []) + url_cfg.get("extra_urls", [])
    if all_source_urls:
        body = body + " Nguồn: " + " | ".join(all_source_urls)

    chunk_text = f"{prefix}\n{body}"

    chunk = {
        "chunk_id": f"{doc_meta.get('file_stem', 'doc')}_t{tidx:03d}_r{row_idx:03d}",
        "source_file": doc_meta.get("file_name", ""),
        "program_type": program_type,
        "admission_year": year,
        "table_id": table.get("table_id", ""),
        "row_index": row_idx,
        "section_name": section,
        "segment_context": seg,
        "row_identifiers": row_identifiers,
        "code_info": code_info,
        "footnotes": table.get("footnote_symbols", []),
        "source_urls": url_cfg.get("source_urls", []),
        "extra_urls": url_cfg.get("extra_urls", []),
        "text": chunk_text,
    }

    issues = []
    if code_info and code_info["code_needs_verification"]:
        issues.append(f"mã cần xác minh: {code_info['code_raw']} -> {code_info['code_corrected']}")
    if not row_identifiers.get("ten_nganh") and not row_identifiers.get("ma_xtuyen"):
        issues.append("thiếu identifier ngành/mã")
    if code_info and code_info["code_raw"] != code_info["code_corrected"]:
        issues.append(f"mã OCR bị sửa: {code_info['code_raw']}")

    if issues:
        chunk["needs_review"] = issues

    return chunk


def chunk_document(doc_dict: dict, whitelist: Dict[str, List[str]], source_urls_config: Dict[str, dict] = None) -> List[dict]:
    docling_out = doc_dict.get("docling_output", {})
    tables = docling_out.get("tables", [])
    doc_meta = dict(doc_dict.get("file_metadata", {}))
    doc_meta["table_annotation_global"] = " ".join(docling_out.get("table_annotations", [])).strip()

    chunks: List[dict] = []
    for tidx, table in enumerate(tables):
        header_count, header_paths = detect_header_rows(table)
        grid = build_cell_map(table)
        max_row = max((c.get("start_row_offset_idx", 0) for c in table.get("data", {}).get("table_cells", [])), default=-1)
        for r in range(header_count, max_row + 1):
            chunk = make_chunk_for_row(table, r, header_paths, grid, doc_meta, whitelist, tidx, source_urls_config)
            if chunk:
                chunks.append(chunk)

    logger.info(f"Chunking complete: {len(chunks)} chunks from {len(tables)} tables.")
    return chunks


def write_spot_check_report(chunks: List[dict], output_path: Path) -> None:
    flagged = [c for c in chunks if c.get("needs_review") or (c.get("code_info") and c["code_info"].get("code_needs_verification"))]
    lines = [
        "# Spot-check Report — Các dòng cần kiểm tra thủ công",
        "",
        f"Tổng chunk: **{len(chunks)}** | Cần kiểm tra: **{len(flagged)}**",
        "",
        "## Danh sách cần xác minh",
        "",
    ]
    for i, c in enumerate(flagged, 1):
        ci = c.get("code_info")
        lines.append(f"### {i}. `{c['chunk_id']}`")
        lines.append(f"- Section: {c['section_name']}")
        lines.append(f"- Row: {c['row_index']}")
        if c.get("needs_review"):
            lines.append(f"- Vấn đề: {', '.join(c['needs_review'])}")
        if ci:
            lines.append(f"- Mã: `{ci['code_raw']}` → `{ci['code_corrected']}` ({ci['code_reason']})")
        lines.append("")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    logger.info(f"Spot-check report written: {output_path}")


def process_all_documents(
    input_dir: str = "backend/data/processed/pastedown",
    output_dir: str = "backend/data/processed/chunks",
    target_stem: Optional[str] = None,
):
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    whitelist = load_whitelist()
    source_urls_config = load_source_urls()

    json_files = list(input_path.glob("*.json"))
    if target_stem:
        json_files = [f for f in json_files if target_stem in f.name]
        logger.info(f"Single-file mode: targeting '{target_stem}', found {len(json_files)} file(s).")
    else:
        logger.info(f"Found {len(json_files)} pastedown documents for chunking.")

    for file in json_files:
        logger.info(f"Processing: {file.name}")
        doc_dict = load_json(str(file))
        if not doc_dict:
            continue
        chunks = chunk_document(doc_dict, whitelist, source_urls_config)
        out_doc = {
            "source_file": doc_dict.get("file_metadata", {}),
            "chunks": chunks,
            "chunk_count": len(chunks),
            "generated_by": "chunking.py (step 6)",
        }
        dest_path = output_path / file.name.replace("_docling.json", "_chunks.json")
        save_json(out_doc, str(dest_path))
        report_path = output_path / file.name.replace("_docling.json", "_spot_check_report.md")
        write_spot_check_report(chunks, report_path)


if __name__ == "__main__":
    process_all_documents()
