import os
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from utils import logger, save_json, load_json


# ---------------------------------------------------------------------------
# Helpers: compute num_cols / num_rows from table_cells
# (Docling JSON does NOT export these keys directly — they must be derived)
# ---------------------------------------------------------------------------

def get_num_cols(table: dict) -> int:
    """Computes the number of columns from the maximum end_col_offset_idx."""
    cells = table.get("data", {}).get("table_cells", [])
    if not cells:
        return 0
    return max((c.get("end_col_offset_idx", 0) for c in cells), default=0)


def get_num_rows(table: dict) -> int:
    """Computes the number of rows from the maximum end_row_offset_idx."""
    cells = table.get("data", {}).get("table_cells", [])
    if not cells:
        return 0
    return max((c.get("end_row_offset_idx", 0) for c in cells), default=0)


def get_page_no(table: dict) -> int:
    """Extracts page number of a table element."""
    prov = table.get("prov", [])
    if prov and "page_no" in prov[0]:
        return prov[0]["page_no"]
    return 0


def has_heading_between(doc_dict: dict, table_a: dict, table_b: dict) -> bool:
    """
    Checks if there is a section header between table_a and table_b.
    Uses BOTTOMLEFT coordinate system: larger 't' value = higher on page.
    """
    page_a = get_page_no(table_a)
    page_b = get_page_no(table_b)

    prov_a = table_a.get("prov", [])
    prov_b = table_b.get("prov", [])

    # In BOTTOMLEFT origin: 'b' (bottom coord) is the lower edge of the element
    # 't' (top coord) is the upper edge — larger t = higher on page
    y_bottom_a = prov_a[0]["bbox"]["b"] if prov_a and "bbox" in prov_a[0] else 0  # lower edge of table A
    y_top_b = prov_b[0]["bbox"]["t"] if prov_b and "bbox" in prov_b[0] else 0     # upper edge of table B

    for text in doc_dict["docling_output"].get("texts", []):
        if text.get("label") != "section_header":
            continue
        prov = text.get("prov", [])
        if not prov:
            continue
        p = prov[0].get("page_no", 0)
        h_t = prov[0]["bbox"]["t"] if "bbox" in prov[0] else 0  # top of heading

        # Heading is between A and B if:
        if page_a < p < page_b:
            # On a page strictly between A and B
            return True
        elif p == page_a and p == page_b:
            # Same page: heading between bottom-of-A and top-of-B
            # In BOTTOMLEFT: y_bottom_a < h_t < y... wait
            # table_a is above table_b => table_a's 'b' (bottom) > table_b's 't' (top)
            # A heading between them: h_t < y_bottom_a AND h_t > y_top_b
            if y_top_b < h_t < y_bottom_a:
                return True
        elif p == page_a:
            # Heading on page_a, below table_a (h_t < y_bottom_a)
            if h_t < y_bottom_a:
                return True
        elif p == page_b:
            # Heading on page_b, above table_b (h_t > y_top_b)
            if h_t > y_top_b:
                return True

    return False


def get_header_row_text(table: dict, row_idx: int = 0) -> List[str]:
    """Extracts texts of cells in a specific row index."""
    cells = table.get("data", {}).get("table_cells", [])
    row_cells = [c for c in cells if c.get("start_row_offset_idx") == row_idx]
    row_cells.sort(key=lambda c: c.get("start_col_offset_idx", 0))
    return [c.get("text", "").strip().lower() for c in row_cells]


def headers_are_similar(table_a: dict, table_b: dict) -> bool:
    """Checks if B's first row is highly similar to A's first row."""
    header_a = get_header_row_text(table_a, 0)
    header_b = get_header_row_text(table_b, 0)

    if not header_a or not header_b:
        return False

    # Calculate overlap ratio
    common = set(header_a) & set(header_b)
    if len(header_a) == len(header_b) and len(header_a) > 0:
        if len(common) / len(header_a) >= 0.7:
            return True
    return False


def tables_are_same_logical_table(doc_dict: dict, table_a: dict, table_b: dict) -> bool:
    """
    Checks if consecutive tables should be merged.
    Conditions:
    - Same computed column count (derived from table_cells)
    - Consecutive pages (page_b - page_a == 1)
    - No section heading in between
    """
    # FIX: Use computed values instead of missing JSON keys
    cols_a = get_num_cols(table_a)
    cols_b = get_num_cols(table_b)

    page_a = get_page_no(table_a)
    page_b = get_page_no(table_b)

    same_col_count = (cols_a == cols_b) and (cols_a > 0)
    consecutive_pages = (page_b - page_a) == 1

    if not same_col_count or not consecutive_pages:
        return False

    # Check if there is a heading between them
    if has_heading_between(doc_dict, table_a, table_b):
        return False

    return True


def merge_two_tables(table_a: dict, table_b: dict) -> dict:
    """Merges table_b into table_a, adjusting row offsets and deduplicating headers if needed."""
    merged = dict(table_a)

    cells_a = table_a.get("data", {}).get("table_cells", [])
    cells_b = table_b.get("data", {}).get("table_cells", [])

    # FIX: Compute rows/cols from cells instead of relying on missing JSON keys
    rows_a = get_num_rows(table_a)
    rows_b = get_num_rows(table_b)
    num_cols = get_num_cols(table_a)

    # Check if B starts with a redundant header row
    b_starts_with_header = False
    first_row_b_cells = [c for c in cells_b if c.get("start_row_offset_idx") == 0]
    if any(c.get("column_header", False) for c in first_row_b_cells):
        if headers_are_similar(table_a, table_b):
            b_starts_with_header = True

    merged_cells = []

    # Add all cells of A
    for cell in cells_a:
        merged_cells.append(dict(cell))

    # Add cells of B with row offset adjustment
    if b_starts_with_header:
        row_offset = rows_a - 1
        for cell in cells_b:
            if cell.get("start_row_offset_idx") == 0:
                continue  # Skip redundant header row
            new_cell = dict(cell)
            new_cell["start_row_offset_idx"] += row_offset
            new_cell["end_row_offset_idx"] += row_offset
            merged_cells.append(new_cell)
        new_num_rows = rows_a + rows_b - 1
    else:
        row_offset = rows_a
        for cell in cells_b:
            new_cell = dict(cell)
            new_cell["start_row_offset_idx"] += row_offset
            new_cell["end_row_offset_idx"] += row_offset
            merged_cells.append(new_cell)
        new_num_rows = rows_a + rows_b

    # Merge metadata and provenance
    prov_a = table_a.get("prov", [])
    prov_b = table_b.get("prov", [])
    merged_prov = prov_a + prov_b

    captions = table_a.get("captions", []) + table_b.get("captions", [])
    footnotes = table_a.get("footnotes", []) + table_b.get("footnotes", [])
    annotations = table_a.get("annotations", []) + table_b.get("annotations", [])

    merged["prov"] = merged_prov
    merged["captions"] = captions
    merged["footnotes"] = footnotes
    merged["annotations"] = annotations
    merged["data"] = {
        "table_cells": merged_cells,
        # Store computed values explicitly for downstream steps
        "num_rows": new_num_rows,
        "num_cols": num_cols,
        "orientation": table_a.get("data", {}).get("orientation", "PORTRAIT"),
    }

    # Store merge metadata for debugging / validation
    merged["_merged_from_pages"] = sorted(set(
        [get_page_no(table_a)] + [p.get("page_no", 0) for p in prov_b]
    ))
    merged["_merged"] = True

    return merged


def merge_tables_in_document(doc_dict: dict) -> dict:
    """Iterates through document tables and merges adjacent split tables."""
    tables = doc_dict["docling_output"].get("tables", [])
    if not tables:
        return doc_dict

    # Sort tables by page number, then by vertical position (top to bottom).
    # BOTTOMLEFT origin: larger 't' = higher on page => sort by -t to go top-to-bottom.
    def get_sort_key(t):
        prov = t.get("prov", [])
        page = prov[0].get("page_no", 0) if prov else 0
        y = prov[0]["bbox"]["t"] if prov and "bbox" in prov[0] else 0
        return (page, -y)  # earlier page first, then top-to-bottom

    tables.sort(key=get_sort_key)

    merged_tables = []
    skip_indices = set()
    merged_count = 0

    for i, table in enumerate(tables):
        if i in skip_indices:
            continue

        current = table
        j = i + 1
        while j < len(tables) and tables_are_same_logical_table(doc_dict, current, tables[j]):
            logger.info(
                f"  Merging table[{i}] (page {get_page_no(current)}, "
                f"{get_num_cols(current)} cols) with table[{j}] "
                f"(page {get_page_no(tables[j])}, {get_num_cols(tables[j])} cols)"
            )
            current = merge_two_tables(current, tables[j])
            skip_indices.add(j)
            merged_count += 1
            j += 1

        merged_tables.append(current)

    doc_dict["docling_output"]["tables"] = merged_tables
    doc_dict["metadata_preprocessed"] = doc_dict.get("metadata_preprocessed", {})
    doc_dict["metadata_preprocessed"]["tables_merged_count"] = merged_count
    doc_dict["metadata_preprocessed"]["tables_total_after_merge"] = len(merged_tables)

    file_name = doc_dict.get("file_metadata", {}).get("file_name", "unknown")
    logger.info(
        f"[{file_name}] Merge complete: {merged_count} merges, "
        f"{len(merged_tables)} tables remaining."
    )
    return doc_dict


def process_all_documents(
    input_dir: str = "backend/data/processed/docling",
    output_dir: str = "backend/data/processed/merged",
    target_stem: Optional[str] = None,
):
    """
    Reads all parsed JSON documents, merges split tables, and saves the results.

    Args:
        input_dir: Directory containing Docling output JSON files.
        output_dir: Directory to write merged JSON files.
        target_stem: If provided, only process the file matching this stem (for single-file testing).
    """
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    json_files = list(input_path.glob("*.json"))

    if target_stem:
        json_files = [f for f in json_files if target_stem in f.name]
        logger.info(f"Single-file mode: targeting '{target_stem}', found {len(json_files)} file(s).")
    else:
        logger.info(f"Found {len(json_files)} parsed documents for table merging.")

    for file in json_files:
        logger.info(f"Processing: {file.name}")
        doc_dict = load_json(str(file))
        if not doc_dict:
            continue

        merged_doc = merge_tables_in_document(doc_dict)
        dest_path = output_path / file.name
        save_json(merged_doc, str(dest_path))


if __name__ == "__main__":
    process_all_documents()
