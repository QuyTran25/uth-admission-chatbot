"""
Export Derived Artifacts — JSON là single source of truth

Input : backend/data/processed/chunks/*_chunks.json
Output: cùng thư mục:
  - *_chunks.jsonl        : 1 chunk/dòng, nạp thẳng vào BM25/dense/hybrid index (giữ đủ metadata)
  - *_chunks.md           : bản đọc markdown cho spot-check thủ công
  - fulltext.txt          : concat text thuần, CHỈ để grep nhanh (KHÔNG dùng làm input index)

Nguyên tắc: JSON gốc sửa 1 chỗ -> chạy lại script này để đồng bộ mọi derived.
"""
import json
from pathlib import Path
from typing import Optional

from utils import logger, save_json, load_json


def export_derived(chunks_doc: dict, base_output: Path) -> None:
    """Sinh JSONL + MD + fulltext từ chunks_doc (JSON gốc)."""
    chunks = chunks_doc.get("chunks", [])
    source = chunks_doc.get("source_file", {}).get("file_name", "unknown")

    # 1) JSONL
    jsonl_path = base_output.with_suffix(".jsonl")
    with open(jsonl_path, "w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    logger.info(f"JSONL: {jsonl_path} ({len(chunks)} lines)")

    # 2) Markdown (bản đọc cho spot-check)
    md_path = base_output.with_suffix(".md")
    lines = [
        f"# Chunks — {source}",
        "",
        f"Tổng: **{len(chunks)}** chunk",
        "",
    ]
    for i, c in enumerate(chunks, 1):
        lines.append(f"## {i}. `{c['chunk_id']}`")
        lines.append(f"- Section: {c['section_name']}")
        lines.append(f"- Năm: {c['admission_year']} | Hệ: {c['program_type']}")
        ci = c.get("code_info")
        if ci:
            lines.append(
                f"- Mã: `{ci.get('ma_nganh', ci.get('code_raw', 'N/A'))}` "
                f"(cần xác minh: {ci.get('code_needs_verification', ci.get('code_corrected', 'N/A'))})"
            )
        if c.get("needs_review"):
            lines.append(f"- ⚠️ Cần review: {', '.join(c['needs_review'])}")
        all_urls = (c.get("source_urls") or []) + (c.get("extra_urls") or [])
        if all_urls:
            lines.append(f"- Nguồn: {' | '.join(all_urls)}")
        lines.append("")
        lines.append("```text")
        lines.append(c["text"])
        lines.append("```")
        lines.append("")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    logger.info(f"Markdown: {md_path}")

    # 3) Fulltext (chỉ grep)
    txt_path = base_output.parent / "fulltext.txt"
    with open(txt_path, "a", encoding="utf-8") as f:
        for c in chunks:
            f.write(c["text"] + "\n\n")
    logger.info(f"Fulltext append: {txt_path}")


def process_all_documents(
    input_dir: str = "backend/data/processed/chunks",
    target_stem: Optional[str] = None,
    fresh_fulltext: bool = True,
):
    """Export derived cho tất cả (hoặc 1) file chunks JSON."""
    input_path = Path(input_dir)
    input_path.mkdir(parents=True, exist_ok=True)

    json_files = list(input_path.glob("*_chunks.json"))
    if target_stem:
        json_files = [f for f in json_files if target_stem in f.name]
        logger.info(f"Single-file mode: targeting '{target_stem}', found {len(json_files)} file(s).")
    else:
        logger.info(f"Found {len(json_files)} chunks documents for export.")

    # Fulltext: xoá file cũ nếu fresh
    fulltext_path = input_path / "fulltext.txt"
    if fresh_fulltext and fulltext_path.exists():
        fulltext_path.unlink()
        logger.info("Removed old fulltext.txt (fresh rebuild).")

    for file in json_files:
        logger.info(f"Processing: {file.name}")
        chunks_doc = load_json(str(file))
        if not chunks_doc:
            continue
        base_output = file.with_name(file.name.replace("_chunks.json", "_chunks"))
        export_derived(chunks_doc, base_output)


if __name__ == "__main__":
    process_all_documents()
