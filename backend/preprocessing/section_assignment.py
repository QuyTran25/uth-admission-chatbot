import os
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from utils import logger, save_json, load_json


def build_table_ref_map(tables: List[dict]) -> Dict[str, dict]:
    """
    Builds a lookup map from self_ref string to table object.
    This is needed because after merging, the tables list may no longer
    correspond 1-to-1 with the original index used in body $ref strings.
    """
    return {t["self_ref"]: t for t in tables if "self_ref" in t}


def find_nearest_heading_geometric(doc_dict: dict, table: dict) -> str:
    """
    Geometric fallback: Finds the nearest section header *before* the table.

    Coordinate system: BOTTOMLEFT origin.
      - 't' (top coord) has a LARGER value when the element is HIGHER on the page.
      - 'b' (bottom coord) has a SMALLER value when lower on the page.

    A heading is "before" a table if:
      - It appears on an earlier page, OR
      - It is on the same page with a HIGHER 't' value (= visually above the table).

    We pick the heading that is closest from above (highest page + highest y on that page).
    """
    prov_t = table.get("prov", [])
    if not prov_t:
        return "Unknown Section"

    table_page = prov_t[0].get("page_no", 0)
    # In BOTTOMLEFT: 't' is the top edge of the element (larger = higher on page)
    table_top_y = prov_t[0]["bbox"]["t"] if "bbox" in prov_t[0] else 0

    candidates = []
    for text in doc_dict["docling_output"].get("texts", []):
        if text.get("label") != "section_header":
            continue
        prov = text.get("prov", [])
        if not prov or "bbox" not in prov[0]:
            continue

        h_page = prov[0].get("page_no", 0)
        h_t = prov[0]["bbox"]["t"]  # top of heading (larger = higher on page)
        h_text = text.get("text", "").strip()

        if not h_text:
            continue

        # A heading is "before" the table if:
        if h_page < table_page:
            # Heading is on an earlier page
            candidates.append((h_page, h_t, h_text))
        elif h_page == table_page and h_t > table_top_y:
            # Heading is on the same page but ABOVE the table (larger t = higher up)
            candidates.append((h_page, h_t, h_text))

    if not candidates:
        return "Unknown Section"

    # Sort by (page ascending, t ascending) — the LAST entry is the nearest heading above.
    # On the same page: heading with the SMALLEST t that is still > table_top_y is nearest.
    # So we want: sort by page asc, then by t asc among same-page candidates. The last is closest.
    candidates.sort(key=lambda x: (x[0], x[1]))
    return candidates[-1][2]


def assign_sections_to_tables(doc_dict: dict) -> dict:
    """
    Assigns a section header metadata field ('section_name') to each table.

    Strategy:
    1. Walk the body children in reading order.
       - Track the most recently seen section_header text as `current_section`.
       - When a table $ref is encountered, look it up in the ref map and assign.
    2. For any table not assigned via tree traversal (e.g., merged tables whose
       original self_ref no longer matches), fall back to geometric proximity.
    """
    docling_out = doc_dict.get("docling_output", {})
    tables = docling_out.get("tables", [])
    if not tables:
        return doc_dict

    # Initialise table_id and section_name for all tables
    for idx, table in enumerate(tables):
        table["table_id"] = f"table_{idx + 1:03d}"
        table["section_name"] = None

    # Build a map: self_ref string -> table object for O(1) lookup
    table_ref_map = build_table_ref_map(tables)

    # Also build a secondary map by index for tables whose self_ref appears in body children
    # (tables that were merged keep the self_ref of their first constituent table)
    texts = docling_out.get("texts", [])
    text_ref_map = {t.get("self_ref", ""): t for t in texts if "self_ref" in t}

    # Step 1: Walk body children in document reading order
    current_section = "Unknown Section"

    def traverse_elements(elements: List[dict]):
        nonlocal current_section
        for el in elements:
            ref = el.get("$ref", "")
            if not ref:
                continue

            # Determine element type from ref path (e.g., "#/texts/5" -> "texts")
            parts = ref.strip("#/").split("/")
            if len(parts) < 2:
                continue
            ref_type, ref_idx_str = parts[0], parts[1]

            if ref_type == "texts":
                # Look up text element directly
                resolved_text = text_ref_map.get(ref)
                if resolved_text is None:
                    # Fallback: resolve by index
                    try:
                        resolved_text = texts[int(ref_idx_str)]
                    except (IndexError, ValueError):
                        resolved_text = None

                if resolved_text and resolved_text.get("label") == "section_header":
                    new_section = resolved_text.get("text", "").strip()
                    if new_section:
                        current_section = new_section
                        logger.debug(f"  Section header updated: '{current_section}'")

            elif ref_type == "tables":
                # Look up table by self_ref (handles merged tables correctly)
                resolved_table = table_ref_map.get(ref)
                if resolved_table is not None and resolved_table.get("section_name") is None:
                    resolved_table["section_name"] = current_section
                    logger.debug(
                        f"  Table '{resolved_table.get('table_id')}' assigned to section: '{current_section}'"
                    )

            elif ref_type == "groups":
                # Groups contain nested children — recurse into them
                group_list = docling_out.get("groups", [])
                try:
                    group = group_list[int(ref_idx_str)]
                    traverse_elements(group.get("children", []))
                except (IndexError, ValueError):
                    pass

    body_children = docling_out.get("body", {}).get("children", [])
    traverse_elements(body_children)

    # Step 2: Geometric fallback for any table that still has no section_name
    unassigned_count = 0
    for table in tables:
        if not table.get("section_name"):
            fallback_section = find_nearest_heading_geometric(doc_dict, table)
            table["section_name"] = fallback_section
            unassigned_count += 1
            logger.warning(
                f"  Table '{table.get('table_id')}' used geometric fallback -> '{fallback_section}'"
            )

    assigned_count = len(tables) - unassigned_count
    logger.info(
        f"Section assignment: {assigned_count}/{len(tables)} tables assigned via reading order, "
        f"{unassigned_count} via geometric fallback."
    )
    return doc_dict


def process_all_documents(
    input_dir: str = "backend/data/processed/merged",
    output_dir: str = "backend/data/processed/section",
    target_stem: Optional[str] = None,
):
    """
    Reads all merged JSON documents, assigns sections to tables, and saves results.

    Args:
        input_dir: Directory containing merged JSON files.
        output_dir: Directory to write section-annotated JSON files.
        target_stem: If provided, only process the file matching this stem.
    """
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    json_files = list(input_path.glob("*.json"))

    if target_stem:
        json_files = [f for f in json_files if target_stem in f.name]
        logger.info(f"Single-file mode: targeting '{target_stem}', found {len(json_files)} file(s).")
    else:
        logger.info(f"Found {len(json_files)} merged documents for section assignment.")

    for file in json_files:
        logger.info(f"Processing: {file.name}")
        doc_dict = load_json(str(file))
        if not doc_dict:
            continue

        result_doc = assign_sections_to_tables(doc_dict)
        dest_path = output_path / file.name
        save_json(result_doc, str(dest_path))


if __name__ == "__main__":
    process_all_documents()
