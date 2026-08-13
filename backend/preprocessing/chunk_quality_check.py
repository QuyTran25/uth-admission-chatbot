"""
chunk_quality_check.py — Kiểm tra tự động 4 tiêu chí chất lượng chunk (Mục 5.1)

Input : backend/data/processed/chunks/*.jsonl
Output: backend/data/processed/chunks/quality_report.md

4 tiêu chí:
  1. Self-contained   : chunk có prefix [Năm|Hệ|Section], không thiếu context
  2. Structure-preserving: không có ký tự rác OCR còn sót, không có ô trống vô nghĩa
  3. LLM-readable     : độ dài đủ, câu văn mạch lạc, không có raw OCR artifact
  4. Retrievable      : chứa ít nhất 1 thực thể định danh (năm, hệ, tên ngành / mã)

Usage:
  python backend/preprocessing/chunk_quality_check.py
  python backend/preprocessing/chunk_quality_check.py --dir backend/data/processed/chunks
"""

import re
import sys
import json
import argparse
from pathlib import Path
from typing import List, Dict, Tuple
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Tiêu chí kiểm tra
# ---------------------------------------------------------------------------

# Regex prefix chuẩn: [Năm XXXX | Hệ ... | Section]
PREFIX_PATTERN = re.compile(r"^\[Năm \d{4}\s*\|", re.MULTILINE)
# Dấu hiệu OCR rác còn sót trong text (không nên xuất hiện sau Bước 4/5)
OCR_ARTIFACTS = re.compile(r"\b(?:_{3,}|={3,})\b")
# Ký hiệu trơ nghĩa — * giữa chữ/số (inline, KHÔNG phải bullet đầu dòng)
# Pattern: * hoặc ** hoặc *** nằm giữa ký tự (không phải đầu dòng sau khoảng trắng)
BARE_SYMBOLS = re.compile(r"(?<=[\w\d])[*]{1,3}(?=[\w\d])")
# Độ dài tối thiểu (ký tự) để chunk có ý nghĩa
MIN_TEXT_LEN = 30
# Các từ khoá thực thể tối thiểu phải có để chunk retrievable
ENTITY_FIELDS = ("admission_year", "program_type")


@dataclass
class CheckResult:
    chunk_id: str
    source_file: str
    passed: Dict[str, bool] = field(default_factory=dict)
    issues: List[str] = field(default_factory=list)

    @property
    def all_passed(self) -> bool:
        return all(self.passed.values())

    @property
    def pass_count(self) -> int:
        return sum(1 for v in self.passed.values() if v)


# ---------------------------------------------------------------------------
# 4 hàm kiểm tra tiêu chí
# ---------------------------------------------------------------------------

def check_self_contained(chunk: dict) -> Tuple[bool, List[str]]:
    """
    Tiêu chí 1 — Self-contained:
    - text phải có prefix [Năm XXXX | ...]
    - admission_year và program_type không được None/rỗng
    """
    issues = []
    text = chunk.get("text", "")
    year = chunk.get("admission_year")
    prog = chunk.get("program_type", "")

    if not PREFIX_PATTERN.search(text):
        issues.append("Thiếu prefix [Năm XXXX | Hệ | Section] trong text")
    if not year:
        issues.append("admission_year bị None/rỗng")
    if not prog:
        issues.append("program_type bị None/rỗng")

    return len(issues) == 0, issues


def check_structure_preserving(chunk: dict) -> Tuple[bool, List[str]]:
    """
    Tiêu chí 2 — Structure-preserving:
    - Không còn ký hiệu OCR trơ nghĩa (** *** ___ ===)
    - Với chunk loại table_row: phải có ít nhất 1 cặp "key: value"
    - section_name không được rỗng
    """
    issues = []
    text = chunk.get("text", "")
    section = chunk.get("section_name", "")
    chunk_type = chunk.get("chunk_type", "")

    if BARE_SYMBOLS.search(text):
        issues.append("Còn ký hiệu ký tự trơn nghĩa (*, **, ***) chưa resolve")
    if not section:
        issues.append("section_name rỗng — mất ngữ cảnh mục")
    if chunk_type == "table_row":
        # Phải có ít nhất 1 cặp header: value
        if not re.search(r".+:\s*.+", text):
            issues.append("Chunk table_row không có cặp 'header: value' nào")

    return len(issues) == 0, issues


def check_llm_readable(chunk: dict) -> Tuple[bool, List[str]]:
    """
    Tiêu chí 3 — LLM-readable:
    - text đủ dài (>= MIN_TEXT_LEN ký tự sau strip)
    - Không có OCR artifact dạng chuỗi ký tự lạ
    - Không toàn bộ là whitespace / số
    """
    issues = []
    text = chunk.get("text", "").strip()

    if len(text) < MIN_TEXT_LEN:
        issues.append(f"Text quá ngắn ({len(text)} ký tự < {MIN_TEXT_LEN})")
    if OCR_ARTIFACTS.search(text):
        issues.append("Phát hiện OCR artifact (==, ___, v.v.) trong text")
    # Kiểm tra text có nội dung thực sự không (không chỉ là số/ký hiệu)
    alpha_count = sum(1 for c in text if c.isalpha())
    if alpha_count < 5:
        issues.append("Text không có nội dung chữ cái có nghĩa (< 5 ký tự alpha)")

    return len(issues) == 0, issues


def check_retrievable(chunk: dict) -> Tuple[bool, List[str]]:
    """
    Tiêu chí 4 — Retrievable:
    - Phải có ít nhất 1 field thực thể định danh (admission_year, program_type)
    - Text phải chứa ít nhất 1 từ khoá tuyển sinh (ngành / mã / phương thức)
    - source_urls không được rỗng (để trích dẫn nguồn)
    """
    issues = []
    text = chunk.get("text", "").lower()

    # Kiểm tra metadata fields
    missing_fields = [f for f in ENTITY_FIELDS if not chunk.get(f)]
    if missing_fields:
        issues.append(f"Thiếu field định danh: {', '.join(missing_fields)}")

    keywords = ["ngành", "mã", "chỉ tiêu", "điểm", "học phí", "xét tuyển",
                "chương trình", "nhập học", "học bổng", "cơ sở", "liên hệ",
                # Sau đại học / liên kết quốc tế
                "thạc sĩ", "tiến sĩ", "nghiên cứu sinh", "cao học", "hồ sơ",
                "môn thi", "ngoại ngữ", "luận văn", "luận án", "chuyên ngành",
                "đăng ký", "nộp hồ sơ", "tuyển sinh", "liên kết", "quốc tế",
                "học viên", "đào tạo", "tốt nghiệp", "bằng cấp", "điều kiện",
                # Các từ bổ sung cho văn bản chung và đề cương
                "nghiên cứu", "dự tuyển", "thông báo", "hiệu trưởng", "nơi nhận",
                "văn bản", "ban hành", "thông tin"]
    has_keyword = any(kw in text for kw in keywords)
    if not has_keyword:
        issues.append("Text không chứa từ khoá tuyển sinh nhận dạng được")

    # source_urls cần có (để Attribution Gate trích dẫn)
    src = chunk.get("source_urls", [])
    if not src:
        issues.append("source_urls rỗng — không thể trích dẫn nguồn")

    return len(issues) == 0, issues


# ---------------------------------------------------------------------------
# Kiểm tra 1 chunk
# ---------------------------------------------------------------------------

CRITERIA = [
    ("self_contained",       check_self_contained),
    ("structure_preserving", check_structure_preserving),
    ("llm_readable",         check_llm_readable),
    ("retrievable",          check_retrievable),
]


def check_chunk(chunk: dict) -> CheckResult:
    result = CheckResult(
        chunk_id=chunk.get("chunk_id", "unknown"),
        source_file=chunk.get("source_file", ""),
    )
    for name, fn in CRITERIA:
        passed, issues = fn(chunk)
        result.passed[name] = passed
        if not passed:
            result.issues.extend([f"[{name}] {i}" for i in issues])
    return result


# ---------------------------------------------------------------------------
# Load & chạy toàn bộ
# ---------------------------------------------------------------------------

def load_chunks_from_jsonl(jsonl_path: Path) -> List[dict]:
    chunks = []
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    chunks.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return chunks


def run_quality_check(chunks_dir: str = "backend/data/processed/chunks") -> None:
    chunks_path = Path(chunks_dir)
    jsonl_files = sorted(chunks_path.glob("*.jsonl"))

    if not jsonl_files:
        print(f"[ERROR] Không tìm thấy *.jsonl trong {chunks_dir}")
        sys.exit(1)

    all_results: List[CheckResult] = []
    file_stats: Dict[str, dict] = {}

    for jf in jsonl_files:
        chunks = load_chunks_from_jsonl(jf)
        results = [check_chunk(c) for c in chunks]
        all_results.extend(results)
        failed = [r for r in results if not r.all_passed]
        file_stats[jf.name] = {
            "total": len(results),
            "failed": len(failed),
            "pass_rate": (len(results) - len(failed)) / len(results) * 100 if results else 0,
        }

    _write_report(all_results, file_stats, chunks_path / "quality_report.md")
    _print_summary(all_results, file_stats)


# ---------------------------------------------------------------------------
# Sinh báo cáo Markdown
# ---------------------------------------------------------------------------

def _write_report(results: List[CheckResult], file_stats: dict, out_path: Path) -> None:
    total = len(results)
    failed_all = [r for r in results if not r.all_passed]
    passed_all = total - len(failed_all)

    # Pass rate per criterion
    crit_pass: Dict[str, int] = {name: 0 for name, _ in CRITERIA}
    for r in results:
        for name in crit_pass:
            if r.passed.get(name):
                crit_pass[name] += 1

    lines = [
        "# Quality Report — Kiểm tra 4 tiêu chí chunk (Mục 5.1)",
        "",
        f"**Tổng chunk:** {total} | **Pass all:** {passed_all} ({passed_all/total*100:.1f}%) | "
        f"**Cần xem xét:** {len(failed_all)} ({len(failed_all)/total*100:.1f}%)",
        "",
        "## Pass rate theo tiêu chí",
        "",
        "| Tiêu chí | Pass | Tổng | % |",
        "|---|---|---|---|",
    ]
    crit_labels = {
        "self_contained": "Self-contained",
        "structure_preserving": "Structure-preserving",
        "llm_readable": "LLM-readable",
        "retrievable": "Retrievable",
    }
    for name, _ in CRITERIA:
        p = crit_pass[name]
        lines.append(f"| {crit_labels[name]} | {p} | {total} | {p/total*100:.1f}% |")

    lines += [
        "",
        "## Thống kê theo file",
        "",
        "| File | Tổng | Fail | Pass rate |",
        "|---|---|---|---|",
    ]
    for fname, stats in sorted(file_stats.items()):
        lines.append(
            f"| `{fname}` | {stats['total']} | {stats['failed']} | {stats['pass_rate']:.1f}% |"
        )

    if failed_all:
        lines += [
            "",
            f"## Chi tiết chunk cần xem xét ({len(failed_all)} chunks)",
            "",
        ]
        for i, r in enumerate(failed_all, 1):
            lines.append(f"### {i}. `{r.chunk_id}`")
            lines.append(f"- **File:** `{r.source_file}`")
            lines.append(f"- **Tiêu chí pass:** {r.pass_count}/{len(CRITERIA)}")
            lines.append("- **Vấn đề:**")
            for issue in r.issues:
                lines.append(f"  - {issue}")
            lines.append("")
    else:
        lines += ["", "## ✅ Tất cả chunk đã pass 4 tiêu chí!", ""]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[INFO] Report written → {out_path}")


def _print_summary(results: List[CheckResult], file_stats: dict) -> None:
    total = len(results)
    failed = [r for r in results if not r.all_passed]
    print(f"\n{'='*55}")
    print(f"  QUALITY CHECK — {total} chunks từ {len(file_stats)} file(s)")
    print(f"{'='*55}")
    print(f"  Pass all 4 criteria : {total - len(failed):>5} ({(total-len(failed))/total*100:.1f}%)")
    print(f"  Cần xem xét         : {len(failed):>5} ({len(failed)/total*100:.1f}%)")
    print(f"{'='*55}")
    for name, _ in CRITERIA:
        labels = {"self_contained": "Self-contained    ",
                  "structure_preserving": "Structure-pres.  ",
                  "llm_readable": "LLM-readable     ",
                  "retrievable": "Retrievable      "}
        p = sum(1 for r in results if r.passed.get(name))
        print(f"  {labels[name]}: {p:>5}/{total} ({p/total*100:.1f}%)")
    print(f"{'='*55}\n")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Chunk quality check — 4 tiêu chí Mục 5.1")
    parser.add_argument(
        "--dir",
        type=str,
        default="backend/data/processed/chunks",
        help="Thư mục chứa *.jsonl chunks (default: backend/data/processed/chunks)",
    )
    args = parser.parse_args()
    run_quality_check(args.dir)
