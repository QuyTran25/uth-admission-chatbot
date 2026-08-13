"""
retrieval_service.py — Core retrieval logic: BM25, Dense, Hybrid (RRF + Weighted)

Hỗ trợ:
  - search_bm25(query, top_k, filters)
  - search_dense(query, top_k, filters)
  - search_hybrid(query, top_k, filters, fusion_method="rrf"|"weighted", alpha=0.6)

Metadata filter theo admission_year và program_type (post-filter).
Default admission_year=2026 theo Mục 2.1 đề cương.
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np

from app.core.config import settings
from app.core.index_store import index_store

logger = logging.getLogger("retrieval_service")


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class ScoredChunk:
    chunk_id: str
    score: float
    text: str
    admission_year: Optional[int]
    program_type: str
    section_name: str
    source_file: str
    source_urls: List[str] = field(default_factory=list)
    extra_urls: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "chunk_id": self.chunk_id,
            "score": round(self.score, 6),
            "text": self.text,
            "metadata": {
                "admission_year": self.admission_year,
                "program_type": self.program_type,
                "section_name": self.section_name,
                "source_file": self.source_file,
                "source_urls": self.source_urls,
                "extra_urls": self.extra_urls,
            },
        }


# ---------------------------------------------------------------------------
# Metadata filter (Mục 2.1 đề cương)
# ---------------------------------------------------------------------------

def apply_filters(
    meta_list: List[dict],
    filters: dict,
) -> Tuple[List[dict], dict]:
    """
    Filter metadata list theo admission_year và program_type.

    Mặc định năm 2026 nếu user không chỉ rõ năm (Mục 2.1 đề cương).
    Trả về (filtered_list, response_meta) để tầng Generation biết year bị default.
    """
    response_meta = {}

    # Default admission_year = 2026 nếu không được chỉ rõ
    year = filters.get("admission_year")
    if not year:
        year = settings.DEFAULT_ADMISSION_YEAR
        response_meta["year_defaulted"] = True
        response_meta["year_used"] = year
        logger.debug(f"admission_year không được chỉ rõ — default sang {year}")

    filtered = meta_list
    if year:
        filtered = [m for m in filtered if m.get("admission_year") == year]
    prog = filters.get("program_type")
    if prog:
        filtered = [m for m in filtered if m.get("program_type") == prog]

    return filtered, response_meta


def _meta_to_scored(meta: dict, score: float) -> ScoredChunk:
    return ScoredChunk(
        chunk_id=meta.get("chunk_id", ""),
        score=score,
        text=meta.get("text", ""),
        admission_year=meta.get("admission_year"),
        program_type=meta.get("program_type", ""),
        section_name=meta.get("section_name", ""),
        source_file=meta.get("source_file", ""),
        source_urls=meta.get("source_urls", []),
        extra_urls=meta.get("extra_urls", []),
    )


# ---------------------------------------------------------------------------
# BM25 search
# ---------------------------------------------------------------------------

def search_bm25(
    query: str,
    top_k: int = 5,
    filters: Optional[dict] = None,
) -> Tuple[List[ScoredChunk], dict]:
    """
    BM25 sparse retrieval.
    Returns (results, response_meta).
    """
    filters = filters or {}
    bm25 = index_store.bm25
    meta_list = index_store.bm25_meta

    # Apply metadata filter
    filtered_meta, resp_meta = apply_filters(meta_list, filters)

    if not filtered_meta:
        logger.warning("BM25: không có chunk nào sau khi filter.")
        return [], resp_meta

    # Map filtered indices về original corpus indices
    filtered_indices = [m["bm25_id"] for m in filtered_meta]

    # Tokenize query
    tokenized_query = index_store.tokenize_query(query)

    # BM25 score toàn bộ corpus rồi mask theo filtered_indices
    all_scores = bm25.get_scores(tokenized_query)
    # Chỉ giữ score của indices trong filtered_meta
    filtered_scores = [(i, all_scores[i]) for i in filtered_indices]
    filtered_scores.sort(key=lambda x: x[1], reverse=True)

    # Top-k
    top = filtered_scores[:top_k]
    results = []
    for corpus_idx, score in top:
        meta = meta_list[corpus_idx]
        results.append(_meta_to_scored(meta, float(score)))

    return results, resp_meta


# ---------------------------------------------------------------------------
# Dense (FAISS) search
# ---------------------------------------------------------------------------

def search_dense(
    query: str,
    top_k: int = 5,
    filters: Optional[dict] = None,
) -> Tuple[List[ScoredChunk], dict]:
    """
    Dense vector retrieval qua FAISS.
    Post-filter: search top_k * EXPAND_FACTOR rồi filter theo metadata.
    """
    EXPAND_FACTOR = 5  # over-fetch để bù hao do post-filter
    filters = filters or {}
    faiss_index = index_store.faiss_index
    meta_list = index_store.faiss_meta

    # Pre-compute filter set (faiss_id)
    filtered_meta, resp_meta = apply_filters(meta_list, filters)
    valid_ids = {m["faiss_id"] for m in filtered_meta}

    if not valid_ids:
        logger.warning("Dense: không có chunk nào sau khi filter.")
        return [], resp_meta

    # Encode query
    query_vec = index_store.encode_query(query)  # shape (1, D), normalized

    # Over-fetch
    search_k = min(top_k * EXPAND_FACTOR, faiss_index.ntotal)
    scores, indices = faiss_index.search(query_vec, search_k)

    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx < 0:
            continue
        if idx not in valid_ids:
            continue
        meta = meta_list[idx]
        results.append(_meta_to_scored(meta, float(score)))
        if len(results) >= top_k:
            break

    return results, resp_meta


# ---------------------------------------------------------------------------
# Hybrid: RRF + Weighted Sum
# ---------------------------------------------------------------------------

def _rrf_score(rank: int, k: int = None) -> float:
    """Reciprocal Rank Fusion score."""
    k = k or settings.RRF_K
    return 1.0 / (k + rank)


def search_hybrid(
    query: str,
    top_k: int = 5,
    filters: Optional[dict] = None,
    fusion_method: str = "rrf",  # "rrf" | "weighted"
    alpha: float = None,         # dùng khi fusion_method="weighted"
) -> Tuple[List[ScoredChunk], dict]:
    """
    Hybrid Retrieval: kết hợp BM25 + Dense.

    fusion_method="rrf"      : Reciprocal Rank Fusion (default, robust, không cần normalize)
    fusion_method="weighted" : alpha * dense_score + (1-alpha) * bm25_norm_score

    Trả về (results, response_meta).
    """
    alpha = alpha if alpha is not None else settings.DENSE_WEIGHT

    # Fetch nhiều hơn từ cả hai để RRF hoạt động tốt
    fetch_k = max(top_k * 3, 20)

    bm25_results, resp_meta_b = search_bm25(query, top_k=fetch_k, filters=filters)
    dense_results, resp_meta_d = search_dense(query, top_k=fetch_k, filters=filters)

    # Merge response_meta (ưu tiên bm25's vì cùng filter logic)
    resp_meta = {**resp_meta_d, **resp_meta_b}

    if fusion_method == "rrf":
        combined = _fuse_rrf(bm25_results, dense_results)
    else:
        combined = _fuse_weighted(bm25_results, dense_results, alpha)

    return combined[:top_k], resp_meta


def _fuse_rrf(
    bm25_results: List[ScoredChunk],
    dense_results: List[ScoredChunk],
) -> List[ScoredChunk]:
    """Reciprocal Rank Fusion."""
    scores: Dict[str, float] = {}
    chunk_map: Dict[str, ScoredChunk] = {}

    for rank, chunk in enumerate(bm25_results):
        scores[chunk.chunk_id] = scores.get(chunk.chunk_id, 0.0) + _rrf_score(rank)
        chunk_map[chunk.chunk_id] = chunk

    for rank, chunk in enumerate(dense_results):
        scores[chunk.chunk_id] = scores.get(chunk.chunk_id, 0.0) + _rrf_score(rank)
        chunk_map[chunk.chunk_id] = chunk

    # Sort theo RRF score tổng hợp
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    results = []
    for cid, fused_score in ranked:
        c = chunk_map[cid]
        results.append(ScoredChunk(
            chunk_id=c.chunk_id,
            score=fused_score,
            text=c.text,
            admission_year=c.admission_year,
            program_type=c.program_type,
            section_name=c.section_name,
            source_file=c.source_file,
            source_urls=c.source_urls,
            extra_urls=c.extra_urls,
        ))
    return results


def _fuse_weighted(
    bm25_results: List[ScoredChunk],
    dense_results: List[ScoredChunk],
    alpha: float,
) -> List[ScoredChunk]:
    """
    Weighted Sum: alpha * dense_score + (1-alpha) * bm25_norm_score.
    BM25 scores được min-max normalize trước khi cộng.
    """
    def normalize(scores: List[float]) -> List[float]:
        if not scores:
            return scores
        mn, mx = min(scores), max(scores)
        if mx == mn:
            return [1.0] * len(scores)
        return [(s - mn) / (mx - mn) for s in scores]

    bm25_scores_raw = [c.score for c in bm25_results]
    dense_scores_raw = [c.score for c in dense_results]
    bm25_norm = normalize(bm25_scores_raw)
    dense_norm = normalize(dense_scores_raw)

    scores: Dict[str, float] = {}
    chunk_map: Dict[str, ScoredChunk] = {}

    for chunk, norm_score in zip(bm25_results, bm25_norm):
        scores[chunk.chunk_id] = scores.get(chunk.chunk_id, 0.0) + (1 - alpha) * norm_score
        chunk_map[chunk.chunk_id] = chunk

    for chunk, norm_score in zip(dense_results, dense_norm):
        scores[chunk.chunk_id] = scores.get(chunk.chunk_id, 0.0) + alpha * norm_score
        chunk_map[chunk.chunk_id] = chunk

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    results = []
    for cid, fused_score in ranked:
        c = chunk_map[cid]
        results.append(ScoredChunk(
            chunk_id=c.chunk_id,
            score=fused_score,
            text=c.text,
            admission_year=c.admission_year,
            program_type=c.program_type,
            section_name=c.section_name,
            source_file=c.source_file,
            source_urls=c.source_urls,
            extra_urls=c.extra_urls,
        ))
    return results
