"""
embed_and_index.py — Tạo Embedding và lập chỉ mục FAISS + BM25

Input : backend/data/processed/chunks/*.jsonl
Output: backend/data/index/
    faiss.index       — FAISS IndexFlatIP (dense vectors, L2-normalized)
    faiss_meta.jsonl  — chunk id → metadata mapping (cùng thứ tự FAISS)
    bm25_corpus.pkl   — BM25Okapi serialized
    bm25_meta.jsonl   — chunk id → metadata mapping (cùng thứ tự BM25)

Lưu ý QUAN TRỌNG:
    bkai-foundation-models/vietnamese-bi-encoder build trên PhoBERT tokenizer.
    Văn bản ĐẦU VÀO BẮT BUỘC phải được tách từ (word segmentation) trước
    khi encode, nếu không chất lượng embedding giảm đáng kể (silent bug).
    → Dùng underthesea.word_tokenize(text, format="text") trước model.encode().
    → Cùng output tách từ được tái dùng cho BM25 tokenizer.

Usage:
    python backend/pipeline/embed_and_index.py
    python backend/pipeline/embed_and_index.py --chunks-dir backend/data/processed/chunks
    python backend/pipeline/embed_and_index.py --model BAAI/BGE-M3 --no-word-seg
"""

import argparse
import json
import logging
import pickle
import sys
import time
from pathlib import Path
from typing import List, Dict, Optional

import numpy as np

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("embed_and_index")


# ---------------------------------------------------------------------------
# Config mặc định (có thể override qua CLI)
# ---------------------------------------------------------------------------

DEFAULT_MODEL = "bkai-foundation-models/vietnamese-bi-encoder"
DEFAULT_CHUNKS_DIR = "backend/data/processed/chunks"
DEFAULT_INDEX_DIR = "backend/data/index"
DEFAULT_BATCH_SIZE = 32          # nhỏ hơn 64 để an toàn với RAM CPU
WORD_SEG_DEFAULT = True          # bắt buộc True với bkai; False nếu dùng BGE-M3


# ---------------------------------------------------------------------------
# Helpers — load chunks
# ---------------------------------------------------------------------------

def load_all_chunks(chunks_dir: str) -> List[dict]:
    """Load tất cả *.jsonl trong chunks_dir, dedup theo chunk_id."""
    path = Path(chunks_dir)
    jsonl_files = sorted(path.glob("*.jsonl"))
    if not jsonl_files:
        logger.error(f"Không tìm thấy *.jsonl trong {chunks_dir}")
        sys.exit(1)

    seen_ids = set()
    chunks = []
    for jf in jsonl_files:
        with open(jf, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    chunk = json.loads(line)
                except json.JSONDecodeError:
                    continue
                cid = chunk.get("chunk_id", "")
                if cid and cid not in seen_ids:
                    seen_ids.add(cid)
                    chunks.append(chunk)

    logger.info(f"Loaded {len(chunks)} chunks (dedup) từ {len(jsonl_files)} file(s)")
    return chunks


# ---------------------------------------------------------------------------
# Word segmentation (bắt buộc với bkai PhoBERT)
# ---------------------------------------------------------------------------

def build_segmenter(use_word_seg: bool):
    """
    Trả về hàm segment(text) -> str.
    - use_word_seg=True: dùng underthesea.word_tokenize (bắt buộc với bkai)
    - use_word_seg=False: trả nguyên text (dùng với BGE-M3, multilingual model)
    """
    if not use_word_seg:
        logger.info("Word segmentation: TẮT (phù hợp với multilingual model như BGE-M3)")
        return lambda text: text

    try:
        from underthesea import word_tokenize
        logger.info("Word segmentation: BẬT (underthesea) — bắt buộc với bkai PhoBERT")
        return lambda text: word_tokenize(text, format="text")
    except ImportError:
        logger.warning(
            "underthesea chưa cài! Fallback về whitespace split.\n"
            "  Cài: pip install underthesea\n"
            "  CẢNH BÁO: chất lượng embedding với bkai sẽ giảm đáng kể."
        )
        return lambda text: text


# ---------------------------------------------------------------------------
# Embedding — FAISS index
# ---------------------------------------------------------------------------

def build_faiss_index(
    chunks: List[dict],
    model_name: str,
    batch_size: int,
    segmenter,
    index_dir: Path,
) -> None:
    """
    Encode chunks → L2-normalize → FAISS IndexFlatIP (cosine similarity).
    Lưu: faiss.index, faiss_meta.jsonl
    """
    try:
        import faiss
        from sentence_transformers import SentenceTransformer
    except ImportError as e:
        logger.error(f"Thiếu dependency: {e}. Chạy: pip install faiss-cpu sentence-transformers")
        sys.exit(1)

    logger.info(f"Loading model: {model_name}")
    model = SentenceTransformer(model_name)

    # Tách từ và lấy text
    texts_raw = [c.get("text", "") for c in chunks]
    logger.info("Đang word-segment texts cho embedding...")
    t0 = time.time()
    texts_seg = [segmenter(t) for t in texts_raw]
    logger.info(f"Word segmentation xong: {time.time() - t0:.1f}s")

    # Encode theo batch
    logger.info(f"Encoding {len(texts_seg)} chunks (batch_size={batch_size})...")
    t0 = time.time()
    embeddings = model.encode(
        texts_seg,
        batch_size=batch_size,
        show_progress_bar=True,
        normalize_embeddings=True,   # L2 normalize → IndexFlatIP = cosine
        convert_to_numpy=True,
    )
    logger.info(f"Encoding xong: {time.time() - t0:.1f}s | shape={embeddings.shape}")

    # Build FAISS index
    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings.astype(np.float32))
    logger.info(f"FAISS IndexFlatIP: {index.ntotal} vectors, dim={dim}")

    # Lưu index
    index_path = index_dir / "faiss.index"
    faiss.write_index(index, str(index_path))
    logger.info(f"Saved FAISS index → {index_path}")

    # Lưu metadata (giữ nguyên thứ tự, cùng index với FAISS)
    meta_path = index_dir / "faiss_meta.jsonl"
    with open(meta_path, "w", encoding="utf-8") as f:
        for i, chunk in enumerate(chunks):
            meta = {
                "faiss_id": i,
                "chunk_id": chunk.get("chunk_id", ""),
                "source_file": chunk.get("source_file", ""),
                "program_type": chunk.get("program_type", ""),
                "admission_year": chunk.get("admission_year"),
                "section_name": chunk.get("section_name", ""),
                "source_urls": chunk.get("source_urls", []),
                "extra_urls": chunk.get("extra_urls", []),
                "chunk_type": chunk.get("chunk_type", ""),
                "text": chunk.get("text", ""),
            }
            f.write(json.dumps(meta, ensure_ascii=False) + "\n")
    logger.info(f"Saved FAISS metadata → {meta_path}")

    return texts_seg  # trả lại texts đã segment để BM25 tái dùng


# ---------------------------------------------------------------------------
# BM25 index
# ---------------------------------------------------------------------------

def build_bm25_index(
    chunks: List[dict],
    texts_seg: List[str],
    index_dir: Path,
) -> None:
    """
    Build BM25Okapi từ texts đã segment (tái dùng output của segmenter).
    Lưu: bm25_corpus.pkl, bm25_meta.jsonl
    """
    try:
        from rank_bm25 import BM25Okapi
    except ImportError:
        logger.error("Thiếu rank-bm25. Chạy: pip install rank-bm25")
        sys.exit(1)

    logger.info("Building BM25 corpus...")
    tokenized_corpus = [text.lower().split() for text in texts_seg]

    t0 = time.time()
    bm25 = BM25Okapi(tokenized_corpus)
    logger.info(f"BM25 built: {len(tokenized_corpus)} docs | {time.time() - t0:.1f}s")

    # Lưu BM25 object
    bm25_path = index_dir / "bm25_corpus.pkl"
    with open(bm25_path, "wb") as f:
        pickle.dump(bm25, f)
    logger.info(f"Saved BM25 index → {bm25_path}")

    # Lưu metadata (cùng thứ tự với BM25)
    meta_path = index_dir / "bm25_meta.jsonl"
    with open(meta_path, "w", encoding="utf-8") as f:
        for i, chunk in enumerate(chunks):
            meta = {
                "bm25_id": i,
                "chunk_id": chunk.get("chunk_id", ""),
                "source_file": chunk.get("source_file", ""),
                "program_type": chunk.get("program_type", ""),
                "admission_year": chunk.get("admission_year"),
                "section_name": chunk.get("section_name", ""),
                "source_urls": chunk.get("source_urls", []),
                "extra_urls": chunk.get("extra_urls", []),
                "chunk_type": chunk.get("chunk_type", ""),
                "text": chunk.get("text", ""),
            }
            f.write(json.dumps(meta, ensure_ascii=False) + "\n")
    logger.info(f"Saved BM25 metadata → {meta_path}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Embed chunks → FAISS + BM25 index")
    parser.add_argument(
        "--chunks-dir",
        type=str,
        default=DEFAULT_CHUNKS_DIR,
        help=f"Thư mục chứa *.jsonl chunks (default: {DEFAULT_CHUNKS_DIR})",
    )
    parser.add_argument(
        "--index-dir",
        type=str,
        default=DEFAULT_INDEX_DIR,
        help=f"Thư mục lưu index output (default: {DEFAULT_INDEX_DIR})",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=DEFAULT_MODEL,
        help=f"Tên model SentenceTransformer (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help=f"Batch size cho encoding (default: {DEFAULT_BATCH_SIZE})",
    )
    parser.add_argument(
        "--no-word-seg",
        action="store_true",
        default=False,
        help="Tắt word segmentation (dùng với BGE-M3 hoặc multilingual model)",
    )
    args = parser.parse_args()

    use_word_seg = not args.no_word_seg

    # Cảnh báo nếu dùng bkai mà tắt word seg
    if not use_word_seg and "bkai" in args.model.lower():
        logger.warning(
            "⚠ CẢNH BÁO: --no-word-seg được bật nhưng model là bkai (PhoBERT-based)!\n"
            "  Chất lượng embedding sẽ giảm đáng kể. Bỏ --no-word-seg hoặc chuyển sang BGE-M3."
        )

    index_dir = Path(args.index_dir)
    index_dir.mkdir(parents=True, exist_ok=True)

    # Load chunks
    chunks = load_all_chunks(args.chunks_dir)

    # Build segmenter (chạy 1 lần, dùng chung cho cả FAISS và BM25)
    segmenter = build_segmenter(use_word_seg)

    # P2a: FAISS (trả lại texts đã segment)
    logger.info("\n" + "="*55 + "\n  BƯỚC 1/2: Embedding → FAISS\n" + "="*55)
    texts_seg = build_faiss_index(chunks, args.model, args.batch_size, segmenter, index_dir)

    # P2b: BM25 (tái dùng texts_seg)
    logger.info("\n" + "="*55 + "\n  BƯỚC 2/2: BM25 Index\n" + "="*55)
    build_bm25_index(chunks, texts_seg, index_dir)

    logger.info("\n✅ HOÀN TẤT — Index files:")
    for f in sorted(index_dir.iterdir()):
        size_kb = f.stat().st_size / 1024
        logger.info(f"   {f.name:<30} {size_kb:>8.1f} KB")


if __name__ == "__main__":
    main()
