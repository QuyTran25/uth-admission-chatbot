import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, List

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("preprocessing_pipeline")

# Folder mapping from Vietnamese uppercase to standard lowercase ascii name
FOLDER_MAPPING = {
    "ĐẠI HỌC CHÍNH QUY": "dai_hoc_chinh_quy",
    "ĐẠI HỌC THƯỜNG XUYÊN": "dai_hoc_thuong_xuyen",
    "ĐÀO TẠO SAU ĐẠI HỌC": "sau_dai_hoc",
    "LIÊN KẾT QUỐC TẾ": "lien_ket_quoc_te",
    "THÔNG TIN CHUNG": "thong_tin_chung"
}

# Display name mapping for Vietnamese program types
PROGRAM_TYPE_DISPLAY = {
    "dai_hoc_chinh_quy": "Đại học chính quy",
    "dai_hoc_thuong_xuyen": "Đại học thường xuyên",
    "sau_dai_hoc": "Sau đại học",
    "lien_ket_quoc_te": "Liên kết quốc tế",
    "thong_tin_chung": "Thông tin chung"
}

def get_raw_files(raw_dir: str = "backend/data/raw") -> List[Dict[str, Any]]:
    """
    Recursively scans the raw directory and returns metadata for each file.
    Filters out 'LINK' files and system files.
    """
    raw_path = Path(raw_dir)
    if not raw_path.exists():
        logger.error(f"Raw directory does not exist: {raw_dir}")
        return []

    files_metadata = []
    # Supported file extensions
    supported_extensions = {".pdf", ".docx", ".md", ".txt"}

    for path in raw_path.rglob("*"):
        if path.is_file():
            # Check extension
            if path.suffix.lower() not in supported_extensions:
                continue
            
            # Skip LINK files and hidden system files
            if path.name.startswith("LINK") or path.name.startswith("."):
                continue

            # Identify the program type from the folder name
            parent_folder = path.parent.name
            program_type = FOLDER_MAPPING.get(parent_folder, "unknown")

            # Parse year and metadata from the filename (e.g. 2026_co-so.md)
            parts = path.stem.split("_")
            year = None
            if parts[0].isdigit() and len(parts[0]) == 4:
                year = int(parts[0])

            files_metadata.append({
                "file_path": str(path.resolve()),
                "file_name": path.name,
                "file_stem": path.stem,
                "extension": path.suffix.lower(),
                "program_type": program_type,
                "admission_year": year,
                "parent_folder": parent_folder
            })

    # Sort files: dependencies first, e.g. general info, then by year
    # Sorting by admission_year (None first, then ascending)
    files_metadata.sort(key=lambda x: (x["admission_year"] if x["admission_year"] is not None else 0))
    return files_metadata

def load_json(file_path: str) -> Any:
    """Loads a JSON file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load JSON file {file_path}: {e}")
        return None

def save_json(data: Any, file_path: str) -> bool:
    """Saves data to a JSON file."""
    try:
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"Successfully saved JSON data to {file_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to save JSON to {file_path}: {e}")
        return False


# ============================================================
# Text splitting utilities (shared between chunking.py and simple_chunker.py)
# ============================================================

import re

MAX_TEXT_LEN = 800
MIN_TEXT_LEN = 30

# Tách câu tiếng Việt (giữ dấu chấm/hỏi/chấm than)
_SENTENCE_SPLIT_RE = re.compile(r'(?<=[.!?])\s+')


def split_long_text(text: str, max_len: int = MAX_TEXT_LEN, min_len: int = MIN_TEXT_LEN) -> List[str]:
    """
    Tách text dài thành các đoạn <= max_len, ưu tiên cắt tại ranh giới câu.
    Trả về list các đoạn đã strip, bỏ qua đoạn < min_len.
    """
    text = text.strip()
    if not text:
        return []
    if len(text) <= max_len:
        return [text] if len(text) >= min_len else []

    # 1. Tách thành câu
    sentences = _SENTENCE_SPLIT_RE.split(text)
    # Gộp lại các câu cho tới khi gần max_len
    parts = []
    current = ""
    for sent in sentences:
        sent = sent.strip()
        if not sent:
            continue
        # Nếu 1 câu tự nó đã > max_len -> cắt cứng
        if len(sent) > max_len:
            if current:
                parts.append(current.strip())
                current = ""
            # Cắt cứng câu dài
            for i in range(0, len(sent), max_len):
                sub = sent[i:i+max_len].strip()
                if len(sub) >= min_len:
                    parts.append(sub)
            continue

        # Thử gộp câu vào current
        if current and len(current) + 1 + len(sent) > max_len:
            parts.append(current.strip())
            current = sent
        else:
            current = (current + " " + sent).strip() if current else sent

    if current and len(current) >= min_len:
        parts.append(current.strip())

    return parts
