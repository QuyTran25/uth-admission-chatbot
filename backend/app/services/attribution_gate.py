"""
attribution_gate.py — Lớp kiểm chứng trích dẫn sau LLM (Post-generation Attribution Gate)

Cơ chế kiểm chứng 2 mức độ:
1. Citation Integrity Check (Set Membership):
   - Mỗi [[chunk_id]] mà Gemini trích dẫn bắt buộc phải thuộc tập chunks đã được truy xuất.
   - Tránh việc model hallucinate ra chunk_id không hề có trong ngữ cảnh.
   - Ngưỡng Citation Precision: 0.90 (theo quy chuẩn hệ thống).

2. Lexical Support Check (Factual grounding proxy):
   - Đo độ phủ từ vựng/thực thể quan trọng giữa câu trả lời sinh ra và nội dung các chunk được trích dẫn.
   - Phát hiện các trường hợp câu trả lời bịa đặt nhưng chèn bừa chunk_id hợp lệ.

3. Refusal Bypass Protocol:
   - Các truy vấn từ chối (refused) không sinh thông tin tuyển sinh nên bỏ qua kiểm tra trích dẫn
     và được đánh dấu rõ ràng là `bypassed_refusal`.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger("attribution_gate")

CITATION_PRECISION_THRESHOLD = 0.90
MIN_LEXICAL_SUPPORT_THRESHOLD = 0.15  # Tối thiểu 15% từ khóa quan trọng của câu trả lời phải nằm trong chunk trích dẫn


# ---------------------------------------------------------------------------
# Data class
# ---------------------------------------------------------------------------

@dataclass
class AttributionResult:
    passed: bool
    citation_precision: Optional[float] = None     # None nếu refusal/bypassed, float nếu answer
    total_citations: int = 0
    valid_citations: int = 0
    failed_citations: list[str] = field(default_factory=list)   # chunk_id không tồn tại trong retrieved chunks
    method: str = "citation_integrity_and_lexical"
    lexical_support_score: Optional[float] = None
    is_refusal_bypassed: bool = False


def _fuzzy_match_id(failed_cid: str, retrieved_ids: set[str]) -> str | None:
    """
    Thử fuzzy match một chunk_id không khớp hoàn toàn với retrieved_ids.
    So sánh qua chuẩn hóa hoặc substring/prefix/suffix.
    """
    norm_failed = re.sub(r'[\s_\-]+', '', failed_cid.lower())
    for rid in retrieved_ids:
        norm_rid = re.sub(r'[\s_\-]+', '', rid.lower())
        if norm_failed == norm_rid:
            return rid
        if len(norm_failed) > 5 and len(norm_rid) > 5:
            if norm_failed in norm_rid or norm_rid in norm_failed:
                return rid
    return None


def compute_lexical_support(response_text: str, cited_chunks: list) -> float:
    """
    Tính tỷ lệ từ khóa quan trọng trong câu trả lời xuất hiện trong văn bản các chunk được trích dẫn.
    """
    if not response_text or not cited_chunks:
        return 0.0

    # Lấy các token có nghĩa (độ dài >= 2 ký tự, không tính ký tự đặc biệt)
    tokens = set(re.findall(r'\b[a-zA-Z0-9_\u00C0-\u1EF9]{2,}\b', response_text.lower()))
    stopwords = {"của", "cho", "các", "những", "được", "trong", "theo", "với", "hoặc", "này", "khi", "tại", "một", "có", "là", "và", "để"}
    content_tokens = {t for t in tokens if t not in stopwords}

    if not content_tokens:
        return 1.0

    chunk_corpus = " ".join([getattr(c, "text", "") for c in cited_chunks]).lower()

    supported_count = sum(1 for t in content_tokens if t in chunk_corpus)
    return round(supported_count / len(content_tokens), 4)


# ---------------------------------------------------------------------------
# Gate logic
# ---------------------------------------------------------------------------

def check_attribution(
    cited_ids: list[str],
    retrieved_chunks: list,       # list[ScoredChunk] từ retrieval_service
    response_text: str = "",
    is_refused: bool = False,
) -> AttributionResult:
    """
    Kiểm tra các chunk_id mà Gemini trích dẫn có thực sự tồn tại
    trong danh sách chunks đã được truy xuất và có nâng đỡ nội dung câu trả lời hay không.
    """
    # Nếu Gemini đã từ chối hoặc câu hỏi bị từ chối → đánh dấu bypass rõ ràng
    if is_refused:
        return AttributionResult(
            passed=True,
            citation_precision=None,
            total_citations=0,
            valid_citations=0,
            failed_citations=[],
            method="bypassed_refusal",
            lexical_support_score=None,
            is_refusal_bypassed=True,
        )

    # Tập hợp chunk_id đã truy xuất
    retrieved_map = {c.chunk_id: c for c in retrieved_chunks}
    retrieved_ids = set(retrieved_map.keys())

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
            method="citation_integrity",
            lexical_support_score=0.0,
            is_refusal_bypassed=False,
        )

    # Phân loại valid / invalid citations
    valid = []
    failed = []
    valid_chunk_objs = []
    for cid in cited_ids:
        if cid in retrieved_ids:
            valid.append(cid)
            valid_chunk_objs.append(retrieved_map[cid])
        else:
            failed.append(cid)
            matched_id = _fuzzy_match_id(cid, retrieved_ids)
            if matched_id:
                logger.warning(
                    f"[HALLUCINATED_ID_WARNING] Fuzzy match detected for hallucinated chunk_id '{cid}' "
                    f"(matched retrieved_id '{matched_id}'). Marked INVALID."
                )

    precision = len(valid) / total
    passed_precision = precision >= CITATION_PRECISION_THRESHOLD

    # Kiểm tra Lexical Factual Support
    lexical_score = compute_lexical_support(response_text, valid_chunk_objs) if response_text else 1.0
    passed_lexical = lexical_score >= MIN_LEXICAL_SUPPORT_THRESHOLD if response_text else True

    overall_passed = passed_precision and passed_lexical

    if failed or not passed_lexical:
        logger.warning(
            f"attribution_gate: FAIL (precision={precision:.2f}, lexical_support={lexical_score:.2f}, failed_cids={failed})"
        )
    else:
        logger.info(
            f"attribution_gate: passed ({len(valid)}/{total} valid, precision={precision:.2f}, lexical_support={lexical_score:.2f})"
        )

    return AttributionResult(
        passed=overall_passed,
        citation_precision=round(precision, 4),
        total_citations=total,
        valid_citations=len(valid),
        failed_citations=failed,
        method="citation_integrity_and_lexical",
        lexical_support_score=lexical_score,
        is_refusal_bypassed=False,
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
