"""
simple_chunker.py — Xử lý DOCX và Markdown thành chunks

Input : backend/data/raw/**/*.docx, backend/data/raw/**/*.md  (trừ file LINK*)
Output: backend/data/processed/chunks/{stem}_chunks.json + .jsonl + .md

Chiến lược:
  - DOCX: Trích xuất paragraph + bảng bằng python-docx. 
          Mỗi section (heading) tạo 1 chunk text; mỗi dòng bảng tạo 1 chunk.
  - MD  : Đọc text thô, split theo heading (## hoặc #), mỗi section = 1 chunk.

Cả hai loại đều:
  - Gắn source_urls từ source_urls.json theo program_type
  - Xuất cùng cấu trúc JSON như chunks PDF để thống nhất
"""
import json
import sys
import re
from pathlib import Path
from typing import List, Dict, Optional

sys.path.insert(0, str(Path(__file__).parent))
from utils import logger, save_json, load_json, get_raw_files, FOLDER_MAPPING, split_long_text, MAX_TEXT_LEN, MIN_TEXT_LEN, PROGRAM_TYPE_DISPLAY

SOURCE_URLS_PATH = Path("backend/data/source_urls.json")
OUTPUT_DIR = Path("backend/data/processed/chunks")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_source_urls() -> Dict[str, dict]:
    data = load_json(str(SOURCE_URLS_PATH))
    if not data:
        logger.warning("Cannot load source_urls.json — source_urls sẽ để trống.")
        return {}
    return data


def make_text_suffix(source_urls_cfg: dict) -> str:
    """Tạo dòng Nguồn: từ config."""
    all_urls = source_urls_cfg.get("source_urls", []) + source_urls_cfg.get("extra_urls", [])
    if all_urls:
        return " Nguồn: " + " | ".join(all_urls)
    return ""


def build_prefix(program_type: str, admission_year: Optional[int], section: str) -> str:
    """Xây dựng prefix chuẩn cho chunk [Năm | Hệ | Mục]."""
    prog_display = PROGRAM_TYPE_DISPLAY.get(program_type, program_type)
    year_display = str(admission_year) if admission_year is not None else ""
    return f"[Năm {year_display} | Hệ {prog_display} | {section}]" if year_display else f"[Hệ {prog_display} | {section}]"


def build_chunk(
    chunk_id: str,
    source_file: str,
    program_type: str,
    admission_year: Optional[int],
    section_name: str,
    text: str,
    source_urls_cfg: dict,
    chunk_type: str = "text",
) -> dict:
    suffix = make_text_suffix(source_urls_cfg)
    full_text = text.strip() + suffix
    return {
        "chunk_id": chunk_id,
        "source_file": source_file,
        "program_type": program_type,
        "admission_year": admission_year,
        "section_name": section_name,
        "chunk_type": chunk_type,
        "source_urls": source_urls_cfg.get("source_urls", []),
        "extra_urls": source_urls_cfg.get("extra_urls", []),
        "text": full_text,
    }


# ---------------------------------------------------------------------------
# DOCX processing
# ---------------------------------------------------------------------------

def process_docx(file_info: dict, source_urls_cfg: dict) -> List[dict]:
    try:
        from docx import Document
    except ImportError:
        logger.error("python-docx chưa được cài. Chạy: pip install python-docx")
        return []

    file_path = file_info["file_path"]
    file_stem = file_info["file_stem"]
    program_type = file_info["program_type"]
    admission_year = file_info["admission_year"]
    source_file = file_info["file_name"]

    doc = Document(file_path)
    chunks: List[dict] = []
    current_section = "Thông tin chung"
    current_paragraphs: List[str] = []
    chunk_counter = 0

    def flush_paragraphs():
        nonlocal chunk_counter
        text = "\n".join(current_paragraphs).strip()
        if not text:
            return
        # Tách section dài thành các phần <= MAX_TEXT_LEN, cắt tại ranh giới câu
        parts = split_long_text(text, MAX_TEXT_LEN, MIN_TEXT_LEN)
        for part in parts:
            prefix = build_prefix(program_type, admission_year, current_section)
            full_text = f"{prefix}\n{part}"
            chunks.append(build_chunk(
                chunk_id=f"{file_stem}_s{chunk_counter:03d}",
                source_file=source_file,
                program_type=program_type,
                admission_year=admission_year,
                section_name=current_section,
                text=full_text,
                source_urls_cfg=source_urls_cfg,
                chunk_type="text",
            ))
            chunk_counter += 1

    for element in doc.element.body:
        tag = element.tag.split("}")[-1] if "}" in element.tag else element.tag

        if tag == "p":
            from docx.oxml.ns import qn
            style_name = ""
            # Kiểm tra heading style
            pPr = element.find(qn("w:pPr"))
            if pPr is not None:
                pStyle = pPr.find(qn("w:pStyle"))
                if pStyle is not None:
                    style_name = pStyle.get(qn("w:val"), "")

            # Lấy text của paragraph
            texts = []
            for r in element.findall(".//" + qn("w:t")):
                texts.append(r.text or "")
            para_text = "".join(texts).strip()

            if not para_text:
                continue

            is_heading = style_name.lower().startswith("heading") or style_name.lower().startswith("ti\u00eau \u0111\u1ec1")
            if is_heading:
                flush_paragraphs()
                current_section = para_text
                current_paragraphs = []
            else:
                current_paragraphs.append(para_text)

        elif tag == "tbl":
            # Flush paragraphs trước bảng
            flush_paragraphs()
            current_paragraphs = []

            # Trích xuất bảng
            from docx.oxml.ns import qn
            rows_data = []
            headers = []
            for i, tr in enumerate(element.findall(".//" + qn("w:tr"))):
                row_cells = []
                for tc in tr.findall(".//" + qn("w:tc")):
                    cell_texts = []
                    for t in tc.findall(".//" + qn("w:t")):
                        cell_texts.append(t.text or "")
                    row_cells.append("".join(cell_texts).strip())
                if i == 0:
                    headers = row_cells
                else:
                    rows_data.append(row_cells)

            if not headers:
                continue

            for ridx, row in enumerate(rows_data):
                if not any(row):
                    continue
                kv_parts = []
                for h, v in zip(headers, row):
                    if h and v:
                        kv_parts.append(f"{h}: {v}")
                    elif v:
                        kv_parts.append(v)
                if not kv_parts:
                    continue

                prefix = build_prefix(program_type, admission_year, current_section)
                row_text = f"{prefix}\n" + ". ".join(kv_parts) + "."

                chunks.append(build_chunk(
                    chunk_id=f"{file_stem}_t000_r{ridx:03d}",
                    source_file=source_file,
                    program_type=program_type,
                    admission_year=admission_year,
                    section_name=current_section,
                    text=row_text,
                    source_urls_cfg=source_urls_cfg,
                    chunk_type="table_row",
                ))
                chunk_counter += 1

    # Flush đoạn cuối
    flush_paragraphs()

    logger.info(f"DOCX {source_file}: {len(chunks)} chunks")
    return chunks


# ---------------------------------------------------------------------------
# Markdown processing
# ---------------------------------------------------------------------------

def process_md(file_info: dict, source_urls_cfg: dict) -> List[dict]:
    file_path = file_info["file_path"]
    file_stem = file_info["file_stem"]
    program_type = file_info["program_type"]
    admission_year = file_info["admission_year"]
    source_file = file_info["file_name"]

    content = Path(file_path).read_text(encoding="utf-8").strip()
    if not content:
        return []

    # Split theo heading (## hoặc #)
    sections = re.split(r"\n(?=#{1,3} )", content)
    chunks: List[dict] = []

    for idx, section_text in enumerate(sections):
        section_text = section_text.strip()
        if not section_text:
            continue

        # Lấy tiêu đề section
        lines = section_text.split("\n")
        heading_line = lines[0]
        section_name = re.sub(r"^#+\s*", "", heading_line).strip() or "Thông tin chung"
        body = "\n".join(lines[1:]).strip() if len(lines) > 1 else section_text

        prefix = build_prefix(program_type, admission_year, section_name)

        # Tách body dài thành các phần <= MAX_TEXT_LEN, cắt tại ranh giới câu
        if body:
            parts = split_long_text(body, MAX_TEXT_LEN, MIN_TEXT_LEN)
            for part_idx, part in enumerate(parts):
                full_text = f"{prefix}\n{part}"
                chunks.append(build_chunk(
                    chunk_id=f"{file_stem}_s{idx:03d}_p{part_idx:03d}",
                    source_file=source_file,
                    program_type=program_type,
                    admission_year=admission_year,
                    section_name=section_name,
                    text=full_text,
                    source_urls_cfg=source_urls_cfg,
                    chunk_type="text",
                ))
        else:
            full_text = f"{prefix}\n{section_text}"
            chunks.append(build_chunk(
                chunk_id=f"{file_stem}_s{idx:03d}",
                source_file=source_file,
                program_type=program_type,
                admission_year=admission_year,
                section_name=section_name,
                text=full_text,
                source_urls_cfg=source_urls_cfg,
                chunk_type="text",
            ))

    logger.info(f"MD {source_file}: {len(chunks)} chunks")
    return chunks


# ---------------------------------------------------------------------------
# Export helpers (same format as chunking.py)
# ---------------------------------------------------------------------------

def export_chunks(chunks: List[dict], file_stem: str, output_dir: Path):
    output_dir.mkdir(parents=True, exist_ok=True)

    # JSON (source of truth)
    json_path = output_dir / f"{file_stem}_chunks.json"
    save_json({"chunks": chunks, "chunk_count": len(chunks), "generated_by": "simple_chunker.py"}, str(json_path))

    # JSONL
    jsonl_path = output_dir / f"{file_stem}_chunks.jsonl"
    with open(jsonl_path, "w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")

    # Markdown (human-readable)
    md_path = output_dir / f"{file_stem}_chunks.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# Chunks — {file_stem}\n\nTổng: **{len(chunks)}** chunk\n\n")
        for i, c in enumerate(chunks, 1):
            f.write(f"## {i}. `{c['chunk_id']}`\n")
            f.write(f"- Section: {c.get('section_name', '')}\n")
            f.write(f"- Năm: {c.get('admission_year', '')} | Hệ: {c.get('program_type', '')}\n")
            if c.get("source_urls"):
                f.write(f"- Nguồn: {' | '.join(c['source_urls'])}\n")
            f.write(f"\n```text\n{c['text']}\n```\n\n")

    logger.info(f"Exported {len(chunks)} chunks → {json_path.name}, {jsonl_path.name}, {md_path.name}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def process_all_documents(
    raw_dir: str = "backend/data/raw",
    output_dir: str = "backend/data/processed/chunks",
    target_stem: Optional[str] = None,
):
    source_urls_config = load_source_urls()
    output_path = Path(output_dir)

    all_files = get_raw_files(raw_dir)
    # Chỉ lấy DOCX và MD — bỏ qua PDF (đã xử lý bởi pipeline 7 bước)
    target_files = [
        f for f in all_files
        if f["extension"] in (".docx", ".md")
    ]
    if target_stem:
        target_files = [f for f in target_files if target_stem in f["file_stem"]]
        logger.info(f"Single-file mode: '{target_stem}', found {len(target_files)} file(s).")
    else:
        logger.info(f"Simple chunker: processing {len(target_files)} DOCX/MD files.")

    for file_info in target_files:
        ext = file_info["extension"]
        program_type = file_info["program_type"]
        file_stem = f"{program_type}_{file_info['file_stem']}"
        url_cfg = source_urls_config.get(program_type, {})

        logger.info(f"Processing [{ext}]: {file_info['file_name']}")

        if ext == ".docx":
            chunks = process_docx(file_info, url_cfg)
        elif ext == ".md":
            chunks = process_md(file_info, url_cfg)
        else:
            continue

        if not chunks:
            logger.warning(f"No chunks generated for {file_info['file_name']}")
            continue

        export_chunks(chunks, file_stem, output_path)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Simple Chunker: DOCX + MD → chunks")
    parser.add_argument("--single", type=str, default=None, help="Process only files containing this stem")
    args = parser.parse_args()
    process_all_documents(target_stem=args.single)
