"""
index_store.py — Singleton load FAISS + BM25 index khi app startup

Sử dụng pattern module-level singleton để index chỉ load 1 lần.
Được gọi từ FastAPI lifespan event trong main.py.
"""

import json
import logging
import pickle
import sys
from pathlib import Path
from typing import List, Optional

import numpy as np

from app.core.config import settings

logger = logging.getLogger("index_store")


class IndexStore:
    """
    Singleton giữ FAISS index, BM25 object và metadata của cả hai.
    Load từ backend/data/index/ khi app khởi động.
    """

    def __init__(self):
        self._faiss_index = None
        self._faiss_meta: List[dict] = []
        self._bm25 = None
        self._bm25_meta: List[dict] = []
        self._embed_model = None
        self._segmenter = None
        self._loaded = False

    # ------------------------------------------------------------------
    # Load
    # ------------------------------------------------------------------

    def load(self) -> None:
        """Load FAISS, BM25 và embedding model vào memory."""
        if self._loaded:
            logger.info("IndexStore: đã load rồi, bỏ qua.")
            return

        index_dir = settings.index_dir_path
        self._load_faiss(index_dir)
        self._load_bm25(index_dir)
        self._load_embed_model()
        self._load_segmenter()
        self._loaded = True
        logger.info("IndexStore: load hoàn tất.")

    def _load_faiss(self, index_dir: Path) -> None:
        try:
            import faiss
        except ImportError:
            logger.error("faiss-cpu chưa cài. Chạy: pip install faiss-cpu")
            sys.exit(1)

        faiss_path = index_dir / "faiss.index"
        meta_path = index_dir / "faiss_meta.jsonl"

        if not faiss_path.exists():
            logger.error(f"Không tìm thấy FAISS index: {faiss_path}")
            logger.error("Chạy: python backend/pipeline/embed_and_index.py")
            sys.exit(1)

        self._faiss_index = faiss.read_index(str(faiss_path))
        self._faiss_meta = self._load_jsonl(meta_path)
        logger.info(
            f"FAISS: {self._faiss_index.ntotal} vectors, "
            f"dim={self._faiss_index.d}, "
            f"meta={len(self._faiss_meta)} chunks"
        )

    def _load_bm25(self, index_dir: Path) -> None:
        bm25_path = index_dir / "bm25_corpus.pkl"
        meta_path = index_dir / "bm25_meta.jsonl"

        if not bm25_path.exists():
            logger.error(f"Không tìm thấy BM25 index: {bm25_path}")
            logger.error("Chạy: python backend/pipeline/embed_and_index.py")
            sys.exit(1)

        with open(bm25_path, "rb") as f:
            self._bm25 = pickle.load(f)
        self._bm25_meta = self._load_jsonl(meta_path)
        logger.info(f"BM25: {len(self._bm25_meta)} docs")

    def _load_embed_model(self) -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            logger.error("sentence-transformers chưa cài.")
            sys.exit(1)

        logger.info(f"Loading embedding model: {settings.EMBED_MODEL}")
        self._embed_model = SentenceTransformer(settings.EMBED_MODEL)
        logger.info("Embedding model loaded.")

    def _load_segmenter(self) -> None:
        """Load segmenter giống embed_and_index.py."""
        if not settings.WORD_SEGMENTATION:
            self._segmenter = lambda text: text
            return
        try:
            from underthesea import word_tokenize
            self._segmenter = lambda text: word_tokenize(text, format="text")
            logger.info("Segmenter: underthesea word_tokenize (WORD_SEGMENTATION=True)")
        except ImportError:
            logger.warning("underthesea không có — fallback whitespace. Chất lượng giảm!")
            self._segmenter = lambda text: text

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _load_jsonl(path: Path) -> List[dict]:
        records = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
        return records

    # ------------------------------------------------------------------
    # Public API cho retrieval_service
    # ------------------------------------------------------------------

    @property
    def faiss_index(self):
        return self._faiss_index

    @property
    def faiss_meta(self) -> List[dict]:
        return self._faiss_meta

    @property
    def bm25(self):
        return self._bm25

    @property
    def bm25_meta(self) -> List[dict]:
        return self._bm25_meta

    def encode_query(self, query: str) -> np.ndarray:
        """Segment + encode query → L2-normalized vector."""
        segmented = self._segmenter(query)
        vec = self._embed_model.encode(
            [segmented],
            normalize_embeddings=True,
            convert_to_numpy=True,
        )
        return vec.astype(np.float32)

    def tokenize_query(self, query: str) -> List[str]:
        """Segment + tokenize query cho BM25."""
        segmented = self._segmenter(query)
        return segmented.lower().split()

    @property
    def is_loaded(self) -> bool:
        return self._loaded


# Module-level singleton
index_store = IndexStore()
