"""
make_index_manifest.py — Tạo và cập nhật index_manifest.json, bm25_corpus.jsonl, và index_hashes.json.

Đảm bảo:
1. Chuyển đổi/Lưu trữ corpus BM25 dưới dạng JSONL để loại bỏ hoàn toàn rủi ro pickle (Hướng 1).
2. Lưu metadata cấu hình xây dựng index vào index_manifest.json để IndexStore đối chiếu khi load (Điểm D).
3. Tính toán mã băm SHA-256 fail-closed cho toàn bộ artifacts vào index_hashes.json (Điểm B).
"""

import hashlib
import json
import logging
import pickle
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("make_index_manifest")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
INDEX_DIR = PROJECT_ROOT / "backend" / "data" / "index"

def build_bm25_corpus_jsonl(index_dir: Path) -> Path:
    """Tạo bm25_corpus.jsonl chứa danh sách tokens đã phân tách từ cho từng chunk."""
    meta_path = index_dir / "bm25_meta.jsonl"
    jsonl_path = index_dir / "bm25_corpus.jsonl"
    pkl_path = index_dir / "bm25_corpus.pkl"

    if not meta_path.exists():
        raise FileNotFoundError(f"Không tìm thấy {meta_path}")

    from underthesea import word_tokenize

    logger.info(f"Đang sinh {jsonl_path.name} từ {meta_path.name}...")
    with open(meta_path, "r", encoding="utf-8") as f_in, open(jsonl_path, "w", encoding="utf-8") as f_out:
        for idx, line in enumerate(f_in, start=1):
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            text = record.get("text", "")
            # Tokenize giống quy trình build BM25
            tokens = word_tokenize(text, format="text").lower().split()
            payload = {
                "chunk_id": record.get("chunk_id", ""),
                "tokens": tokens
            }
            f_out.write(json.dumps(payload, ensure_ascii=False) + "\n")

    logger.info(f"Đã tạo thành công {jsonl_path} ({jsonl_path.stat().st_size / 1024:.1f} KB).")
    return jsonl_path


def build_manifest_and_hashes(index_dir: Path) -> None:
    """Tạo index_manifest.json và cập nhật index_hashes.json."""
    try:
        import faiss
    except ImportError:
        raise ImportError("Cần faiss-cpu để đọc thông tin index.")

    faiss_path = index_dir / "faiss.index"
    if not faiss_path.exists():
        raise FileNotFoundError(f"Không tìm thấy {faiss_path}")

    faiss_index = faiss.read_index(str(faiss_path))

    manifest = {
        "embed_model": "bkai-foundation-models/vietnamese-bi-encoder",
        "dimension": int(faiss_index.d),
        "ntotal": int(faiss_index.ntotal),
        "metric_type": "METRIC_INNER_PRODUCT" if faiss_index.metric_type == faiss.METRIC_INNER_PRODUCT else str(faiss_index.metric_type),
        "word_segmentation": True,
        "bm25_format": "jsonl",
        "created_at": datetime.now(timezone.utc).isoformat()
    }

    manifest_path = index_dir / "index_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    logger.info(f"Đã tạo {manifest_path}")

    # Danh mục artifact cần băm (chỉ các file hợp lệ, không dùng pickle)
    target_files = [
        "faiss.index",
        "faiss_meta.jsonl",
        "bm25_corpus.jsonl",
        "bm25_meta.jsonl",
        "index_manifest.json"
    ]

    hashes = {}
    for fname in target_files:
        fpath = index_dir / fname
        if fpath.exists():
            hasher = hashlib.sha256()
            with open(fpath, "rb") as f:
                while chunk := f.read(65536):
                    hasher.update(chunk)
            hashes[fname] = hasher.hexdigest()

    hashes_path = index_dir / "index_hashes.json"
    with open(hashes_path, "w", encoding="utf-8") as f:
        json.dump(hashes, f, indent=2, ensure_ascii=False)
    logger.info(f"Đã cập nhật {hashes_path} cho {len(hashes)} tệp.")


def main():
    build_bm25_corpus_jsonl(INDEX_DIR)
    build_manifest_and_hashes(INDEX_DIR)
    logger.info("Hoàn tất tạo Manifest và Hashes cho toàn bộ index.")

if __name__ == "__main__":
    main()
