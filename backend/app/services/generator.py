"""
generator.py — Sinh câu trả lời từ Gemini dựa trên chunks truy xuất được.

Prompt yêu cầu:
  1. Trả lời trực tiếp, ngắn gọn, dùng ngôn ngữ thân thiện tuyển sinh
  2. Trích dẫn nguồn dưới dạng [[chunk_id]] ngay sau mỗi thông tin
  3. Không bịa đặt — nếu không có thông tin trong context thì nói rõ
  4. Nếu là fallback (năm tương lai) thì cảnh báo dữ liệu chưa cập nhật

Output:
  GenerationResult.answer_text  — câu trả lời thuần text
  GenerationResult.cited_ids    — danh sách chunk_id được trích dẫn
  GenerationResult.is_refused   — True nếu Gemini tự nhận ra out-of-scope
"""

import re
import logging
from dataclasses import dataclass, field

from app.core.gemini_client import gemini_client

logger = logging.getLogger("generator")


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class GenerationResult:
    answer_text: str
    cited_ids: list[str]
    is_refused: bool = False
    raw_response: str = ""


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------

def _build_prompt(
    query: str,
    chunks: list,          # list[ScoredChunk] từ retrieval_service
    filter_year: int | None,
    is_fallback: bool,
) -> str:
    """Xây dựng prompt gửi cho Gemini.

    Chiến lược prompt (A1 — Tuần 6):
      - Quy tắc trích dẫn đặt ĐẦU TIÊN, in hoa để tăng compliance
      - Few-shot examples dùng chunk_id format thật từ corpus
      - Liệt kê danh sách chunk_id hợp lệ để Gemini copy-paste
      - Context block dùng [[chunk_id]] nhất quán với format yêu cầu
    """

    # --- Liệt kê danh sách chunk_id hợp lệ ---
    valid_ids = [chunk.chunk_id for chunk in chunks[:5]]
    valid_ids_str = ", ".join(valid_ids)

    # --- Xây dựng context từ các chunks ---
    context_blocks = []
    for chunk in chunks[:5]:  # Dùng tối đa top-5
        context_blocks.append(
            f"[[{chunk.chunk_id}]]\n"
            f"Nguồn: {chunk.source_file} | Mục: {chunk.section_name} | "
            f"Năm: {chunk.admission_year or 'chung'}\n"
            f"{chunk.text.strip()}"
        )
    context_str = "\n\n---\n\n".join(context_blocks)

    # --- Cảnh báo năm nếu cần ---
    year_note = ""
    if is_fallback:
        year_note = (
            "\n⚠️ LƯU Ý: Câu hỏi hỏi về năm tương lai chưa có trong cơ sở dữ liệu. "
            "Hãy trả lời dựa trên thông tin năm gần nhất có sẵn và NHẮC RÕ rằng "
            "dữ liệu chính thức chưa được công bố.\n"
        )

    prompt = f"""BẮT BUỘC — QUY TẮC TRÍCH DẪN NGUỒN (PHẢI TUÂN THỦ 100%):
- Sau MỖI thông tin cụ thể (điểm chuẩn, học phí, chỉ tiêu, mã ngành, ngày tháng...), BẠN PHẢI ghi nguồn bằng cú pháp [[chunk_id]] ngay sau thông tin đó.
- chunk_id PHẢI là một trong các ID hợp lệ sau: {valid_ids_str}
- KHÔNG ĐƯỢC tự bịa chunk_id. CHỈ dùng chunk_id có trong danh sách trên.
- Nếu một câu trả lời dùng thông tin từ nhiều chunk, PHẢI trích dẫn TỪNG chunk tương ứng.

VÍ DỤ ĐÚNG CÁCH TRÍCH DẪN:
- "Điểm chuẩn ngành Công nghệ thông tin năm 2025 theo phương thức xét tuyển kết hợp là 24.5 điểm [[2025_diem-chuan_dai-hoc-chinh-quy_t000_r005]]."
- "Học phí ngành Logistics năm 2026 là 24.000.000 đồng/năm [[2026_thong-tin-tuyen-sinh_dai-hoc-chinh-quy_t003_r012]]."

VÍ DỤ SAI (KHÔNG LÀM THẾ NÀY):
- "Điểm chuẩn ngành CNTT là 24.5 điểm." ← SAI vì thiếu [[chunk_id]]
- "Điểm chuẩn là 24.5 [[chunk_001]]." ← SAI vì chunk_001 không có trong danh sách ID hợp lệ

---

Bạn là trợ lý tư vấn tuyển sinh của Trường Đại học Giao thông Vận tải TP.HCM (UTH).
Nhiệm vụ: Trả lời câu hỏi của thí sinh dựa HOÀN TOÀN vào thông tin trong phần [DỮ LIỆU THAM KHẢO] bên dưới.
{year_note}
QUY TẮC TRẢ LỜI:
1. Trả lời bằng tiếng Việt, thân thiện, ngắn gọn (tối đa 300 từ).
2. Nếu thông tin không có trong [DỮ LIỆU THAM KHẢO], hãy nói thẳng: "Hiện tại tôi chưa có thông tin về vấn đề này." TUYỆT ĐỐI KHÔNG bịa đặt số liệu.
3. Nếu câu hỏi hoàn toàn ngoài phạm vi tuyển sinh UTH, hãy trả lời bằng chính xác cụm từ: "NGOAI_PHAM_VI"

[DỮ LIỆU THAM KHẢO — Danh sách chunk_id hợp lệ: {valid_ids_str}]
{context_str}

[CÂU HỎI]
{query}

[CÂU TRẢ LỜI]"""

    return prompt


# ---------------------------------------------------------------------------
# Trích xuất chunk_id từ câu trả lời
# ---------------------------------------------------------------------------

def _extract_cited_ids(answer_text: str) -> list[str]:
    """Trích xuất tất cả [[chunk_id]] được đề cập trong câu trả lời."""
    pattern = r'\[\[([^\]]+)\]\]'
    return list(dict.fromkeys(re.findall(pattern, answer_text)))  # unique, giữ thứ tự


# ---------------------------------------------------------------------------
# Hàm chính
# ---------------------------------------------------------------------------

def generate_answer(
    query: str,
    chunks: list,
    filter_year: int | None = None,
    is_fallback: bool = False,
) -> GenerationResult:
    """
    Sinh câu trả lời từ Gemini dựa trên chunks truy xuất được.

    Args:
        query:       Câu hỏi gốc của người dùng
        chunks:      Danh sách ScoredChunk từ retrieval_service
        filter_year: Năm lọc (nếu có)
        is_fallback: True nếu hỏi năm tương lai chưa có dữ liệu

    Returns:
        GenerationResult với answer_text, cited_ids, is_refused
    """
    if not chunks:
        logger.warning(f"generate_answer: không có chunk nào cho query='{query[:50]}'")
        return GenerationResult(
            answer_text="Hiện tại tôi chưa tìm thấy thông tin liên quan trong cơ sở dữ liệu của trường.",
            cited_ids=[],
            is_refused=True,
            raw_response="",
        )

    prompt = _build_prompt(query, chunks, filter_year, is_fallback)
    logger.debug(f"Prompt length: {len(prompt)} chars")

    try:
        raw = gemini_client.generate(prompt)
    except Exception as e:
        logger.error(f"Gemini generation failed: {e}")
        raise

    # Kiểm tra nếu Gemini tự nhận diện câu hỏi ngoài phạm vi
    is_refused = "NGOAI_PHAM_VI" in raw

    cited_ids = _extract_cited_ids(raw)

    # Nếu không có trích dẫn và chứa cụm từ từ chối/không có thông tin
    refusal_keywords = ["chưa có thông tin", "không có thông tin", "chưa tìm thấy", "không tìm thấy", "chưa được công bố", "chưa công bố", "chưa hỗ trợ", "không hỗ trợ"]
    if not cited_ids and any(kw in raw.lower() for kw in refusal_keywords):
        is_refused = True

    # Làm sạch câu trả lời
    answer_text = raw.replace("NGOAI_PHAM_VI", "").strip()
    if is_refused and "NGOAI_PHAM_VI" in raw:
        answer_text = "Câu hỏi này nằm ngoài phạm vi tư vấn tuyển sinh của UTH. Mình chỉ có thể hỗ trợ các thông tin liên quan đến tuyển sinh của trường."

    logger.info(
        f"Generated answer: {len(answer_text)} chars, "
        f"cited={cited_ids}, refused={is_refused}"
    )

    return GenerationResult(
        answer_text=answer_text,
        cited_ids=cited_ids,
        is_refused=is_refused,
        raw_response=raw,
    )
