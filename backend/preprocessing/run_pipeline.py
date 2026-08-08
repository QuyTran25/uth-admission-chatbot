"""
run_pipeline.py — Orchestrator cho pipeline bước 1 → 7

Usage:
  .venv\Scripts\python.exe backend/preprocessing/run_pipeline.py \
      --single dai_hoc_chinh_quy_2026 \
      --from-step 1

Steps:
  1 = docling_parsing
  2 = merge_tables
  3 = section_assignment
  4 = resolve_footnotes
  5 = paste_down
  6 = chunking
  7 = export_derived (JSONL/MD/fulltext)
"""
import argparse
import sys
from pathlib import Path

# Ensure module dir on sys.path for `from utils import ...`
sys.path.insert(0, str(Path(__file__).parent))

from utils import logger  # noqa: E402
import parser as docling_parser  # noqa: E402
import merge_tables  # noqa: E402
import section_assignment  # noqa: E402
import resolve_footnotes  # noqa: E402
import paste_down  # noqa: E402
import chunking  # noqa: E402
import export_derived  # noqa: E402
import simple_chunker  # noqa: E402


STEPS = {
    "1": ("Docling Parsing", docling_parser.parse_all_documents),
    "2": ("Merge Tables", merge_tables.process_all_documents),
    "3": ("Section Assignment", section_assignment.process_all_documents),
    "4": ("Resolve Footnotes", resolve_footnotes.process_all_documents),
    "5": ("Paste-down + Segment", paste_down.process_all_documents),
    "6": ("Chunking", chunking.process_all_documents),
    "7": ("Export Derived", export_derived.process_all_documents),
    "8": ("Simple Chunker (DOCX/MD)", simple_chunker.process_all_documents),
}


def main():
    parser = argparse.ArgumentParser(description="UTH preprocessing pipeline runner")
    parser.add_argument("--single", type=str, default=None,
                        help="Only process files whose name contains this stem (e.g. dai_hoc_chinh_quy_2026)")
    parser.add_argument("--from-step", type=str, default="1",
                        help="Step to start from (1|2|3|4|5|6|7). Default 1.")
    args = parser.parse_args()

    start = args.from_step
    if start not in STEPS:
        logger.error(f"Invalid --from-step {start}. Choose from {list(STEPS)}")
        sys.exit(1)

    # Chạy tuần tự từ step start -> 7
    for step_key in sorted(STEPS.keys()):
        if step_key >= start:
            name, func = STEPS[step_key]
            logger.info(f"\n{'='*60}\nBƯỚC {step_key}: {name}\n{'='*60}")
            if step_key == "1":
                # parser.py calls argument single_stem
                func(single_stem=args.single)
            else:
                func(target_stem=args.single)

    logger.info("\nPipeline hoàn tất!")


if __name__ == "__main__":
    main()

