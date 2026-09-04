"""
attribution_gate.py — Lớp 2 kiểm chứng sau LLM (Post-generation Gate)

Kiểm tra tính xác thực của câu trả lời bằng 2 phương pháp:

1. Chunk ID check (áp dụng cho tất cả):
   - Mỗi [[chunk_id]] Gemini trích dẫn phải tồn tại trong tập chunks đã truy xuất
   - Không phụ thuộc LLM thêm — đối chiếu trực tiếp

2. Phương pháp phân loại kết quả:
   - passed=True:  Tất cả chunk_id hợp lệ VÀ citation_precision >= ngưỡng
   - passed=False: Có ít nhất 1 chunk_id không tồn tại HOẶC không trích dẫn gì cả
                   → Hệ thống trả về "không tìm thấy thông tin đủ tin cậy"

Ngưỡng Citation Precision: 0.90 (theo đề cương mục (2))
"""

import logging
from dataclasses import dataclass, field

logger = logging.getLogger("attribution_gate")

CITATION_PRECISION_THRESHOLD = 0.90


# ---------------------------------------------------------------------------
# Data class
# ---------------------------------------------------------------------------

@dataclass
class AttributionResult:
    passed: bool
    citation_precision: float     # valid_citations / total_citations (0.0 nếu không có trích dẫn)
    total_citations: int
    valid_citations: int
    failed_citations: list[str]   # chunk_id không tồn tại trong retrieved chunks
    method: str = "chunk_id"      # Hiện tại chỉ dùng chunk_id check


def _fuzzy_match_id(failed_cid: str, retrieved_ids: set[str]) -> str | None:
    """
    Thử fuzzy match một chunk_id không khớp hoàn toàn với retrieved_ids.
    So sánh qua chuẩn hóa (bỏ khoảng trắng, gạch dưới, gạch ngang, chữ hoa/thường)
    hoặc quan hệ substring/prefix/suffix.
    """
    import re
    norm_failed = re.sub(r'[\s_\-]+', '', failed_cid.lower())
    for rid in retrieved_ids:
        norm_rid = re.sub(r'[\s_\-]+', '', rid.lower())
        if norm_failed == norm_rid:
            return rid
        if len(norm_failed) > 5 and len(norm_rid) > 5:
            if norm_failed in norm_rid or norm_rid in norm_failed:
                return rid
    return None


# ---------------------------------------------------------------------------
# Gate logic
# ---------------------------------------------------------------------------

def check_attribution(
    cited_ids: list[str],
    retrieved_chunks: list,       # list[ScoredChunk] từ retrieval_service
    is_refused: bool = False,
) -> AttributionResult:
    """
    Kiểm tra các chunk_id mà Gemini trích dẫn có thực sự tồn tại
    trong danh sách chunks đã được truy xuất hay không.

    Args:
        cited_ids:        Danh sách chunk_id từ GenerationResult.cited_ids
        retrieved_chunks: Các ScoredChunk trả về từ retrieval_service
        is_refused:       Nếu True (Gemini tự từ chối), Gate luôn passed=True

    Returns:
        AttributionResult
    """
    # Nếu Gemini đã từ chối → không cần kiểm tra attribution
    if is_refused:
        return AttributionResult(
            passed=True,
            citation_precision=1.0,
            total_citations=0,
            valid_citations=0,
            failed_citations=[],
            method="skipped_refused",
        )

    # Tập hợp chunk_id đã truy xuất
    retrieved_ids: set[str] = {c.chunk_id for c in retrieved_chunks}

    total = len(cited_ids)

    # Không trích dẫn gì → Gemini không follow [[chunk_id]] format → Gate kích hoạt FAIL
    if total == 0:
        logger.warning("attribution_gate: cited_ids rỗng — Gemini không trích dẫn [[chunk_id]]. Gate FAIL.")
        return AttributionResult(
            passed=False,
            citation_precision=0.0,
            total_citations=0,
            valid_citations=0,
            failed_citations=[],
            method="chunk_id",
        )

    # Phân loại valid / invalid citations & kiểm tra fuzzy match cho logging
    valid = []
    failed = []
    for cid in cited_ids:
        if cid in retrieved_ids:
            valid.append(cid)
        else:
            failed.append(cid)
            matched_id = _fuzzy_match_id(cid, retrieved_ids)
            if matched_id:
                logger.warning(
                    f"[HALLUCINATED_ID_WARNING] Fuzzy match detected for hallucinated chunk_id '{cid}' "
                    f"(matched retrieved_id '{matched_id}'). "
                    "Fuzzy matches count as INVALID (0.0 precision) to maintain strict admission accuracy."
                )

    precision = len(valid) / total
    passed = precision >= CITATION_PRECISION_THRESHOLD

    if failed:
        logger.warning(
            f"attribution_gate: {len(failed)}/{total} citations không hợp lệ: {failed}"
        )
    else:
        logger.info(
            f"attribution_gate: passed ({len(valid)}/{total} valid, precision={precision:.2f})"
        )

    return AttributionResult(
        passed=passed,
        citation_precision=round(precision, 4),
        total_citations=total,
        valid_citations=len(valid),
        failed_citations=failed,
        method="chunk_id",
    )


def build_citation_list(
    cited_ids: list[str],
    retrieved_chunks: list,
) -> list[dict]:
    """
    Xây dựng danh sách trích dẫn (citations) để trả về cho frontend.
    Chỉ bao gồm các chunk_id hợp lệ (đã được kiểm chứng qua attribution gate).

    Returns:
        list of {chunk_id, source_file, section_name, admission_year, source_urls}
    """
    chunk_map = {c.chunk_id: c for c in retrieved_chunks}
    citations = []
    for cid in cited_ids:
        chunk = chunk_map.get(cid)
        if chunk is None:
            continue  # Bỏ qua chunk không hợp lệ
        citations.append({
            "chunk_id": cid,
            "source_file": chunk.source_file,
            "section_name": chunk.section_name,
            "admission_year": chunk.admission_year,
            "source_urls": chunk.source_urls,
        })
    return citations
