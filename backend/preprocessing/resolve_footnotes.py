"""
Bước 4 — Resolve Chú thích (Footnote Resolution)

Input : backend/data/processed/section/*.json
Output: backend/data/processed/footnotes/*.json

Chức năng:
1. Trích footnote từ `docling_output.texts`:
   - Label `footnote`
   - Hoặc text chứa marker NTC1/NTC2/NTC3 (OCR biến thể: NTCI, NTC3...)
   - Hoặc text bắt đầu bằng "Ghi chú:" (annotation cấp bảng)
2. Build map {symbol: nội_dung_đầy_đủ}
3. Rà từng ô bảng, phát hiện token `NTC1 (*)`, `NTCI(*)`, `NTC3(***)`...
   - Gắn `text_expanded`: text gốc + inline footnote đầy đủ
   - Ghi symbol vào `footnote_symbols` của ô
4. Gắn `table["footnote_symbols"]` và `table["annotations"]` (Ghi chú: cấp bảng)
"""
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from utils import logger, save_json, load_json

# Token NTC trong text: "NTC1 (*)", "NTCI(*)", "NTC3", "NTC 1 (**)"
NTC_TOKEN = re.compile(r"NTC\s*[1I3]?\s*(?:\(\*{1,3}\))?", re.IGNORECASE)
# Marker độc lập (*) (**) (***)
STAR_PATTERN = re.compile(r"\(\*{1,3}\)")
# Annotation cấp bảng
ANNOTATION_PATTERNS = [
    re.compile(r"^Ghi\s*ch[uú]:"),
    re.compile(r"^Ghi\s*ch[uú]\s"),
    re.compile(r"^\*\s*Ghi\s*ch[uú]"),
]


def normalize_symbol(text: str) -> str:
    """
    Chuẩn hoá token NTC -> symbol chuẩn.
    - NTC1/NTCI/NTC 1 -> "ntc1"
    - NTC2 -> "ntc2"
    - NTC3 -> "ntc3"
    Dùng search vì NTC có thể nằm giữa text ("Nhóm môn tự chọn (NTCI):").
    """
    m = re.search(r"NTC\s*([1I3]?)", text, re.IGNORECASE)
    if not m:
        return ""
    num_raw = m.group(1)
    if num_raw == "" or num_raw == "I":
        return "ntc1"  # OCR đọc 1 -> I
    return f"ntc{num_raw}"


def resolve_footnotes(doc_dict: dict) -> dict:
    """Thực hiện resolve chú thích cho toàn bộ document."""
    docling_out = doc_dict.get("docling_output", {})
    texts = docling_out.get("texts", [])
    tables = docling_out.get("tables", [])

    # 1) Gom footnote theo symbol
    footnotes_map: Dict[str, str] = {}
    table_annotations: List[str] = []

    for tx in texts:
        label = tx.get("label", "")
        text = (tx.get("text") or "").strip()
        if not text:
            continue

        is_annotation = any(p.search(text) for p in ANNOTATION_PATTERNS)
        if is_annotation:
            table_annotations.append(text)
            continue

        m_ntc = NTC_TOKEN.search(text)
        m_star = STAR_PATTERN.search(text)

        if m_ntc:
            symbol = normalize_symbol(m_ntc.group(0))
            if symbol:
                footnotes_map[symbol] = text
                continue

        if m_star or label == "footnote":
            key = m_star.group(0) if m_star else f"footnote_{len(footnotes_map) + 1}"
            footnotes_map.setdefault(key, text)
            continue

    # Sắp xếp theo thứ tự ổn định: ntc1, ntc2, ntc3 trước
    ordered = {}
    for k in ["ntc1", "ntc2", "ntc3"]:
        if k in footnotes_map:
            ordered[k] = footnotes_map.pop(k)
    ordered.update(footnotes_map)
    footnotes_map = ordered

    docling_out["resolved_footnotes"] = footnotes_map
    docling_out["table_annotations"] = table_annotations

    # 2) Rà từng ô bảng, thêm text_expanded
    expansions = 0
    for table in tables:
        symbols_used: set = set()
        for cell in table.get("data", {}).get("table_cells", []):
            raw = (cell.get("text") or "").strip()
            if not raw:
                continue
            symbols_found: set = set()
            for m in NTC_TOKEN.finditer(raw):
                sym = normalize_symbol(m.group(0))
                if sym:
                    symbols_found.add(sym)
            if symbols_found:
                symbols_used |= symbols_found
                cell["footnote_symbols"] = sorted(symbols_found)
                expanded = raw
                for sym in sorted(symbols_found):
                    fn_text = footnotes_map.get(sym, "")
                    if fn_text and fn_text not in expanded:
                        expanded = f"{expanded} ({fn_text})"
                cell["text_expanded"] = expanded
                expansions += 1
                logger.debug(f"  Expanded: {raw[:40]}... -> {expanded[:60]}...")
        table["footnote_symbols"] = sorted(symbols_used)

    logger.info(
        f"Resolved footnotes: {len(footnotes_map)} symbols {list(footnotes_map.keys())}, "
        f"{len(table_annotations)} table annotations, {expansions} cell expansions."
    )
    return doc_dict


def process_all_documents(
    input_dir: str = "backend/data/processed/section",
    output_dir: str = "backend/data/processed/footnotes",
    target_stem: Optional[str] = None,
):
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    json_files = list(input_path.glob("*.json"))
    if target_stem:
        json_files = [f for f in json_files if target_stem in f.name]
        logger.info(f"Single-file mode: targeting '{target_stem}', found {len(json_files)} file(s).")
    else:
        logger.info(f"Found {len(json_files)} section documents for footnote resolution.")

    for file in json_files:
        logger.info(f"Processing: {file.name}")
        doc_dict = load_json(str(file))
        if not doc_dict:
            continue
        result_doc = resolve_footnotes(doc_dict)
        dest_path = output_path / file.name
        save_json(result_doc, str(dest_path))


if __name__ == "__main__":
    process_all_documents()
