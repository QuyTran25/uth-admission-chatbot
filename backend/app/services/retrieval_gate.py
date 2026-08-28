"""
retrieval_gate.py — Retrieval Gate service for filtering out-of-scope queries based on retrieval quality.

Cung cấp hàm check_retrieval_quality đánh giá chất lượng chunk dựa trên:
  1. Top-1 score_raw (score gốc chuẩn hóa chưa boost).
  2. BM25 & Dense Consensus (Đồng thuận chunk_id hoặc source_file).
  3. Score margin (top1 vs top2 score_raw).
"""

import logging
from typing import List, Tuple, Optional, Dict
from app.services.retrieval_service import ScoredChunk

logger = logging.getLogger("retrieval_gate")


def check_retrieval_quality(
    chunks: List[ScoredChunk],
    response_meta: dict,
    threshold_default: float,
    threshold_consensus: float,
    consensus_type: str = "exact",  # "exact" | "file"
    margin_threshold: Optional[float] = None,
) -> Tuple[str, Optional[dict]]:
    """
    Đánh giá chất lượng của các tài liệu truy xuất để quyết định đi tiếp hay từ chối.
    
    Args:
        chunks: Danh sách chunks thu được từ retrieve_with_dynamic_routing.
        response_meta: Siêu dữ liệu chứa thông tin top-1 của BM25 và Dense.
        threshold_default: Ngưỡng điểm mặc định khi không đồng thuận.
        threshold_consensus: Ngưỡng điểm thấp hơn khi có đồng thuận.
        consensus_type: Loại đồng thuận ("exact" = trùng chunk_id, "file" = trùng source_file).
        margin_threshold: Ngưỡng margin tối thiểu (nếu sử dụng).
        
    Returns:
        (status, refusal_data)
        - status: "proceed" hoặc "refused"
        - refusal_data: dict chứa chi tiết lý do từ chối, hoặc None.
    """
    # 1. Trường hợp không có chunk nào
    if not chunks:
        logger.warning("Retrieval Gate: Không truy xuất được chunk nào.")
        return "refused", {
            "code": "OUT_OF_SCOPE",
            "refusal_source": "retrieval_gate_score",
            "score_details": {
                "top1_score_raw": 0.0,
                "margin": 0.0,
                "consensus": False,
                "threshold_used": threshold_default,
                "margin_threshold_used": margin_threshold,
                "reason": "no_chunks_retrieved"
            }
        }

    # Lấy thông tin chunk đầu tiên
    top1_chunk = chunks[0]
    top1_score_raw = top1_chunk.score_raw if top1_chunk.score_raw is not None else top1_chunk.score
    
    # 2. Tính toán Consensus
    bm25_top1_cid = response_meta.get("bm25_top1_cid")
    dense_top1_cid = response_meta.get("dense_top1_cid")
    bm25_top1_file = response_meta.get("bm25_top1_file")
    dense_top1_file = response_meta.get("dense_top1_file")

    consensus = False
    if bm25_top1_cid and dense_top1_cid:
        if consensus_type == "exact":
            consensus = (bm25_top1_cid == dense_top1_cid)
        elif consensus_type == "file":
            consensus = (bm25_top1_file and dense_top1_file and bm25_top1_file == dense_top1_file)
        else:
            # Fallback nếu truyền sai type
            consensus = (bm25_top1_cid == dense_top1_cid)

    # 3. Xác định ngưỡng động dựa trên Consensus
    threshold = threshold_consensus if consensus else threshold_default

    # 4. Tính toán Margin (sử dụng score_raw)
    margin = 0.0
    if len(chunks) >= 2:
        top2_chunk = chunks[1]
        top2_score_raw = top2_chunk.score_raw if top2_chunk.score_raw is not None else top2_chunk.score
        margin = top1_score_raw - top2_score_raw
    else:
        margin = top1_score_raw

    # 5. Phân loại từ chối hay đi tiếp
    is_refused = False
    refusal_reason = None

    if top1_score_raw < threshold:
        is_refused = True
        refusal_reason = "score_below_threshold"
    elif margin_threshold is not None and margin < margin_threshold:
        is_refused = True
        refusal_reason = "margin_below_threshold"

    if is_refused:
        refusal_data = {
            "code": "OUT_OF_SCOPE",
            "refusal_source": "retrieval_gate_score",
            "score_details": {
                "top1_score_raw": round(top1_score_raw, 6),
                "margin": round(margin, 6),
                "consensus": consensus,
                "threshold_used": round(threshold, 6),
                "margin_threshold_used": round(margin_threshold, 6) if margin_threshold is not None else None,
                "refusal_reason": refusal_reason
            }
        }
        logger.info(f"Retrieval Gate REFUSED query. Details: {refusal_data['score_details']}")
        return "refused", refusal_data

    logger.debug(f"Retrieval Gate PROCEED. Top1 score_raw: {top1_score_raw:.4f}, Consensus: {consensus}, Threshold: {threshold:.4f}, Margin: {margin:.4f}")
    return "proceed", None
