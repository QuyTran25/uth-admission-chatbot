"""
year_filter.py — Bộ lọc năm tuyển sinh và phân loại câu hỏi

Nhiệm vụ (theo thứ tự ưu tiên):
  1. Nhận diện câu hỏi ngoài phạm vi (out-of-scope) theo chủ đề → từ chối sớm (refused)
  2. Nhận diện các câu hỏi về tương lai chưa công bố (năm > 2026 hoặc từ khóa tương lai) → fallback_warning (proceed + warning)
  3. Nhận diện năm tuyển sinh trong câu hỏi (Regex + từ khóa thời gian)
  4. Phân loại document_type sơ bộ (rule-based keyword matching, 13 loại)
  5. Áp dụng quy tắc định tuyến theo năm (2022-2026)
"""

import re
import logging
from dataclasses import dataclass, field
from typing import List, Optional

logger = logging.getLogger("year_filter")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CURRENT_YEAR = 2026
MIN_SUPPORTED_YEAR = 2022
MAX_SUPPORTED_YEAR = 2026

# Message chuẩn duy nhất cho mọi OUT_OF_SCOPE (Bước 3 - API contract)
OUT_OF_SCOPE_MESSAGE = (
    "Hiện tại mình chưa có thông tin về câu hỏi này. "
    "Để hiểu rõ hơn, bạn vui lòng truy cập trang web "
    "https://tuyensinh.ut.edu.vn/ hoặc liên hệ:\n"
    "☎ 028 3512 8986 – 028 3512 0766\n"
    "📱 0832 488 288\n"
    "✉ Email: tuyensinh@ut.edu.vn\n"
    "Zalo OA: Tuyển Sinh Đại học GTVT TP HCM\n"
    "Fanpage: facebook.com/tuyensinhuth"
)

YEAR_NOT_SUPPORTED_MESSAGE = (
    "Hiện tại hệ thống chỉ hỗ trợ thông tin tuyển sinh từ năm 2022 đến 2026. "
    "Bạn vui lòng liên hệ trực tiếp để được hỗ trợ:\n"
    "☎ 028 3512 8986 – 028 3512 0766\n"
    "📱 0832 488 288"
)

# ---------------------------------------------------------------------------
# Out-of-scope keyword rules (5 nhóm chủ đề, đã loại bỏ nhóm thong_tin_chua_ton_tai)
# ---------------------------------------------------------------------------
_OUT_OF_SCOPE_RULES: List[tuple] = [
    ("du_doan_diem_chuan", [
        "dự đoán", "dự báo", "ước tính điểm", "ước chừng điểm",
        "năm tới điểm", "điểm sẽ là", "đoán điểm",
        "tỷ lệ chọi", "cơ hội đậu", "khả năng đậu",
        "cơ hội trúng tuyển", "xác suất đậu",
    ]),
    ("tu_van_chon_nganh", [
        "nên học ngành nào", "ngành nào hợp", "ngành phù hợp với tôi",
        "ngành phù hợp với em", "hợp với tính cách", "hợp với sở thích",
        "ngành nào dễ học", "ngành nào tốt hơn cho tôi",
        "chọn ngành nào", "em nên chọn ngành",
        "nên thi khối nào để dễ đỗ", "khối nào dễ đậu",
    ]),
    ("co_hoi_viec_lam", [
        "cơ hội việc làm", "triển vọng việc làm", "triển vọng nghề nghiệp",
        "dễ xin việc", "khó xin việc", "ra trường làm gì",
        "ra trường thường làm", "làm ở đâu sau khi ra trường",
        "việc làm sau tốt nghiệp", "nhu cầu tuyển dụng ngành",
    ]),
    ("luong_thu_nhap", [
        "mức lương", "lương sau tốt nghiệp", "lương ra trường",
        "thu nhập sau khi tốt nghiệp", "thu nhập ngành",
        "lương bao nhiêu", "kiếm được bao nhiêu",
        "lương trung bình ngành",
    ]),
    ("so_sanh_truong", [
        "so với trường", "so sánh với trường", "trường nào tốt hơn",
        "trường nào dạy tốt hơn", "xếp hạng trường",
        "ở trường khác", "học phí trường khác",
        "thông tin trường khác",
    ]),
]

# Từ khóa về tương lai chưa công bố -> đi vào luồng fallback_warning chứ không chặn cứng
_FUTURE_KEYWORDS = [
    "năm sau", "năm tới", "tương lai", "sắp tới",
    "chính sách năm sau", "dự kiến năm sau",
    "khi nào có điểm chuẩn", "bao giờ có điểm chuẩn",
]

# ---------------------------------------------------------------------------
# Document type keyword rules (13 loại)
# ---------------------------------------------------------------------------
_DOC_TYPE_RULES: List[tuple] = [
    ("cutoff_score", [
        "điểm chuẩn", "điểm trúng tuyển", "lấy bao nhiêu điểm",
        "điểm đậu", "bao nhiêu điểm", "điểm xét tuyển",
        "điểm của ngành", "điểm ngành",
    ]),
    ("admission_method", [
        "phương thức xét tuyển", "xét tuyển bằng gì", "cách xét tuyển",
        "phương thức tuyển sinh", "xét tuyển thẳng", "xét tuyển kết hợp",
        "tuyển thẳng", "phương án tuyển sinh",
    ]),
    ("admission_condition", [
        "điều kiện xét tuyển", "điều kiện đăng ký", "yêu cầu đầu vào",
        "điều kiện dự tuyển", "tiêu chí xét tuyển", "đủ điều kiện",
        "điều kiện sức khỏe", "điều kiện năng lực",
    ]),
    ("quota", [
        "chỉ tiêu", "số lượng tuyển", "bao nhiêu suất",
        "chỉ tiêu tuyển sinh", "số chỉ tiêu",
    ]),
    ("major", [
        "ngành đào tạo", "các ngành", "ngành học", "mã ngành",
        "mã xét tuyển", "tổ hợp môn", "khối thi",
        "danh sách ngành", "có ngành gì",
    ]),
    ("tuition_fee", [
        "học phí", "chi phí học", "tiền học",
        "học phí mỗi tín chỉ", "học phí toàn khóa",
        "lệ phí xét tuyển", "phí ghi danh",
    ]),
    ("scholarship", [
        "học bổng", "miễn học phí", "hỗ trợ học phí",
        "suất học bổng", "điều kiện học bổng",
    ]),
    ("training_program", [
        "chương trình đào tạo", "khung đào tạo", "tín chỉ",
        "số tín chỉ", "môn học", "thời gian đào tạo",
        "tốt nghiệp cần bao nhiêu tín chỉ", "chương trình chuẩn",
        "chương trình tiên tiến",
    ]),
    ("application_profile", [
        "hồ sơ nhập học", "giấy tờ nhập học", "nộp hồ sơ",
        "hồ sơ đăng ký", "minh chứng xét tuyển", "thủ tục nhập học",
    ]),
    ("timeline", [
        "thời gian tuyển sinh", "lịch tuyển sinh", "thời hạn nộp",
        "deadline", "hạn nộp", "thời gian đăng ký",
        "lịch xét tuyển", "khi nào có kết quả", "mốc thời gian",
        "lịch nộp lệ phí",
    ]),
    ("enrollment_regulation", [
        "quy chế", "quy định nhập học", "điều kiện nhập học",
        "xác nhận nhập học", "nhập học", "rút hồ sơ",
        "quy định xét tuyển",
    ]),
    ("contact_info", [
        "địa chỉ", "cơ sở", "hotline", "số điện thoại",
        "email tuyển sinh", "zalo", "fanpage", "liên hệ",
        "website tuyển sinh", "văn phòng tuyển sinh",
    ]),
    ("general_info", [
        "mã trường", "mã tuyển sinh", "giới thiệu trường",
        "trường ở đâu", "ký túc xá", "campus",
    ]),
]

# Các từ khóa thời gian tương đối → ánh xạ sang năm tuyệt đối
_RELATIVE_YEAR_MAP = {
    "năm nay": CURRENT_YEAR,
    "năm này": CURRENT_YEAR,
    "hiện tại": CURRENT_YEAR,
    "hiện nay": CURRENT_YEAR,
    "kỳ này": CURRENT_YEAR,
    "đợt này": CURRENT_YEAR,
    "năm ngoái": CURRENT_YEAR - 1,
    "năm trước": CURRENT_YEAR - 1,
    "năm vừa rồi": CURRENT_YEAR - 1,
    "năm vừa qua": CURRENT_YEAR - 1,
    "2 năm trước": CURRENT_YEAR - 2,
    "hai năm trước": CURRENT_YEAR - 2,
    "3 năm trước": CURRENT_YEAR - 3,
    "ba năm trước": CURRENT_YEAR - 3,
}

_YEAR_REGEX = re.compile(r"\b(20\d{2})\b")

# Từ khóa gợi ý user muốn so sánh nhiều năm → clarification_needed
_MULTI_YEAR_KEYWORDS = [
    "các năm", "nhiều năm", "qua các năm",
    "so sánh", "so với năm", "từ năm",
    "lịch sử điểm chuẩn",
]

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------
@dataclass
class FilterResult:
    status: str          # "proceed" | "refused" | "clarification_needed"
    code: Optional[str] = None        # "OUT_OF_SCOPE" | "YEAR_NOT_SUPPORTED" | "YEAR_CLARIFICATION_REQUIRED"
    filter_year: Optional[int] = None
    document_type: Optional[str] = None
    warning: Optional[str] = None
    options: List[int] = field(default_factory=list)
    message: Optional[str] = None
    refusal_source: Optional[str] = None  # "year_filter_keyword" | "year_not_supported"


# ---------------------------------------------------------------------------
# Accent removal helper for accent-insensitive matching (Phản biện 4)
# ---------------------------------------------------------------------------
def remove_accents(s: str) -> str:
    """Chuyển tiếng Việt có dấu thành không dấu."""
    s = re.sub(r'[àáạảãâầấậẩẫăằắặẳẵ]', 'a', s)
    s = re.sub(r'[èéẹẻẽêềếệểễ]', 'e', s)
    s = re.sub(r'[ìíịỉĩ]', 'i', s)
    s = re.sub(r'[òóọỏõôồốộổỗơờớợởỡ]', 'o', s)
    s = re.sub(r'[ùúụủũưừứựửữ]', 'u', s)
    s = re.sub(r'[ỳýỵỷỹ]', 'y', s)
    s = re.sub(r'[đ]', 'd', s)
    return s


def _normalize(text: str) -> str:
    """Lowercase + collapse whitespace."""
    return re.sub(r"\s+", " ", text.strip().lower())


def _match_keyword(kw: str, text_no_accent: str) -> bool:
    """
    So khớp keyword bằng regex word boundary trên chuỗi không dấu để tránh match sai substring.
    Ví dụ: 'uoc tinh diem' không được match 'duoc tinh diem'.
    """
    kw_norm = _normalize(kw)
    kw_no_accent = remove_accents(kw_norm)
    pattern = r'\b' + re.escape(kw_no_accent) + r'\b'
    return bool(re.search(pattern, text_no_accent))


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
def _detect_out_of_scope(text_no_accent: str) -> Optional[str]:
    """
    Kiểm tra câu hỏi có thuộc nhóm out-of-scope không.
    """
    for group_name, keywords in _OUT_OF_SCOPE_RULES:
        for kw in keywords:
            if _match_keyword(kw, text_no_accent):
                logger.debug(f"Out-of-scope match: group={group_name}, keyword='{kw}'")
                return group_name
    return None


def _detect_future_request(text_no_accent: str) -> bool:
    """
    Kiểm tra xem câu hỏi có chứa các từ khóa về tương lai chưa công bố không.
    """
    for kw in _FUTURE_KEYWORDS:
        if _match_keyword(kw, text_no_accent):
            logger.debug(f"Future keyword match: '{kw}'")
            return True
    return False


def _detect_year(text_norm: str, text_no_accent: str) -> Optional[int]:
    """
    Nhận diện năm tuyển sinh trong câu hỏi.
    Từ khóa tương đối ("năm ngoái", "năm nay"...) so khớp accent-insensitive
    + word boundary để nhất quán với các hàm detect khác (tránh miss khi user
    gõ không dấu, và tránh match sai substring).
    Số năm tuyệt đối (20xx) không bị ảnh hưởng bởi dấu nên giữ nguyên regex trên text_norm.
    """
    for phrase, year in _RELATIVE_YEAR_MAP.items():
        if _match_keyword(phrase, text_no_accent):
            logger.debug(f"Relative year detected: '{phrase}' → {year}")
            return year

    matches = _YEAR_REGEX.findall(text_norm)
    if matches:
        year = int(matches[0])
        logger.debug(f"Absolute year detected: {year}")
        return year

    return None


def _detect_document_type(text_no_accent: str) -> str:
    """
    Phân loại document_type sơ bộ từ câu hỏi.
    """
    for doc_type, keywords in _DOC_TYPE_RULES:
        for kw in keywords:
            if _match_keyword(kw, text_no_accent):
                logger.debug(f"document_type detected: {doc_type} (keyword='{kw}')")
                return doc_type
    logger.debug("document_type: no match → general_info")
    return "general_info"


def _is_multi_year_request(text_no_accent: str) -> bool:
    """
    Kiểm tra user có chủ động so sánh/hỏi nhiều năm không.
    Dùng accent-insensitive + word boundary để nhất quán với các hàm detect khác.
    """
    return any(_match_keyword(kw, text_no_accent) for kw in _MULTI_YEAR_KEYWORDS)


# ---------------------------------------------------------------------------
# Main public function
# ---------------------------------------------------------------------------
def analyze(query: str) -> FilterResult:
    """
    Phân tích câu hỏi và trả về FilterResult.
    """
    text_norm = _normalize(query)
    text_no_accent = remove_accents(text_norm)
    logger.info(f"year_filter.analyze: '{query[:80]}...' " if len(query) > 80 else f"year_filter.analyze: '{query}'")

    # 1. Out-of-scope keyword check (hỗ trợ không dấu + word boundary)
    oos_group = _detect_out_of_scope(text_no_accent)
    if oos_group:
        logger.info(f"Refused at keyword level: group={oos_group}")
        return FilterResult(
            status="refused",
            code="OUT_OF_SCOPE",
            message=OUT_OF_SCOPE_MESSAGE,
            refusal_source="year_filter_keyword",
        )

    # 2. Nhận diện năm và các từ khóa tương lai
    detected_year = _detect_year(text_norm, text_no_accent)
    is_future = _detect_future_request(text_no_accent) or (detected_year is not None and detected_year > CURRENT_YEAR)

    # 3. Phân loại document_type trước để phục vụ routing
    doc_type = _detect_document_type(text_no_accent)

    # 4. Xử lý câu hỏi tương lai chưa công bố -> luồng fallback_warning
    if is_future:
        future_year_str = str(detected_year) if (detected_year is not None and detected_year > CURRENT_YEAR) else "tới"
        logger.info(f"Future request detected (year={detected_year}) → fallback_warning (2026)")
        return FilterResult(
            status="proceed",
            filter_year=CURRENT_YEAR,
            document_type=doc_type,
            warning=(
                f"Lưu ý: Thông tin tuyển sinh năm {future_year_str} chưa được công bố. "
                f"Dưới đây là thông tin năm {CURRENT_YEAR} để bạn tham khảo."
            ),
        )

    # 5. Xử lý năm quá khứ ngoài tầm hỗ trợ (< 2022)
    if detected_year is not None and detected_year < MIN_SUPPORTED_YEAR:
        logger.info(f"Year not supported: {detected_year}")
        return FilterResult(
            status="refused",
            code="YEAR_NOT_SUPPORTED",
            message=YEAR_NOT_SUPPORTED_MESSAGE,
            refusal_source="year_not_supported",
        )

    # 6. Routing theo document_type + năm (2022-2026)
    if doc_type == "cutoff_score":
        # User chủ động hỏi so sánh nhiều năm — ưu tiên kiểm tra TRƯỚC, bất kể
        # có phát hiện được 1 năm cụ thể hay không. Lý do: _detect_year chỉ lấy
        # năm đầu tiên tìm thấy, nên câu như "so sánh điểm chuẩn 2024 và 2025"
        # vẫn có detected_year=2024 — nếu chặn theo "detected_year is None" sẽ
        # lặng lẽ trả lời chỉ 1 năm, bỏ sót ý so sánh của user.
        if _is_multi_year_request(text_no_accent):
            logger.info("cutoff_score: multi-year request → clarification_needed")
            return FilterResult(
                status="clarification_needed",
                code="YEAR_CLARIFICATION_REQUIRED",
                document_type=doc_type,
                options=[2026, 2025, 2024, 2023, 2022],
                message="Vui lòng chọn năm tuyển sinh bạn muốn tra cứu điểm chuẩn:",
            )

    # Nếu có năm cụ thể (trong khoảng [2022, 2026]) -> Cho phép proceed cho MỌI document_type
    if detected_year is not None:
        logger.info(f"Proceed with detected year {detected_year} for doc_type {doc_type}")
        return FilterResult(
            status="proceed",
            filter_year=detected_year,
            document_type=doc_type,
        )

    # Không rõ năm -> Mặc định CURRENT_YEAR (2026)
    logger.info(f"No year specified, doc_type={doc_type} → default {CURRENT_YEAR}")
    return FilterResult(
        status="proceed",
        filter_year=CURRENT_YEAR,
        document_type=doc_type,
    )
