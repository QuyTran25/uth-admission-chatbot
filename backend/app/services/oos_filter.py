import re
import unicodedata

# Danh sách các trường đại học khác để lọc các câu hỏi so sánh hoặc hỏi thông tin trường khác
OTHER_SCHOOLS = [
    'hutech', 'bach khoa', 'ton duc thang', 'utc2', r'\butc\b',
    'ueh', r'\bdh luat\b', 'su pham ky thuat', 'hang hai viet nam',
    'kinh te tphcm', 'dai hoc luat', 'giao thong van tai ha noi',
    'ngoai bac', r'\bdh kinh te\b', 'rmit', 'greenwich', r'\bfpt\b',
    'huflit', 'hcmue', 'hcmus', 'hcmut',
]

PATTERNS = {
    'du_doan_diem_chuan': [
        r'\bdu doan\b.*\bdiem\b',
        r'\bdu bao\b.*\bdiem\b',
        r'\bdu kien\b.*\bdiem\b',
        r'\bdiem\b.*\bdu doan\b',
        r'\bdiem\b.*\bdu kien\b',
        r'\bdiem\b.*\bdu bao\b',
        r'\bdiem\b.*(tang|giam).*(se|du bao|nam nay)',
        r'\bnam nay\b.*\bdiem\b.*(bao nhieu|la bao)',
        r'\bdiem san\b.*(du bao|du doan)',
        r'\bdu doan\b.*diem san',
        # Loại bỏ các cụm "cần bao nhiêu điểm để đỗ/đậu" vì nhãn dev set coi là in-scope
    ],
    'tu_van_chon_nganh_khoi': [
        r'\bnen chon\b.*(nganh|khoi)',
        r'\bnen hoc\b.*(nganh|truong)',
        r'\bphu hop\b.*(tinh cach|so thich|nang luc)',
        r'\bkhuyen\b.*(em|minh|ban).*(nganh|khoi)',
        r'\btu van\b.*(chon nganh|dinh huong)',
        r'\bchon nganh\b',
        r'\bdinh huong\b.*(nganh|nghe)',
        r'\bkhoi nao\b.*(de|tot hon)',
        r'\bnganh nao\b.*(de|phu hop|tot hon)',
        r'\bnen dang ky\b.*(nganh|khoi)',
        r'\bdang phan van\b.*nganh',
    ],
    'luong_thu_nhap': [
        # Chỉ dùng các cụm từ rõ ràng liên quan đến lương/thu nhập, tránh "lượng" trong "chất lượng"
        r'\bmuc luong\b',
        r'\bluong khoi diem\b',
        r'\bluong ra truong\b',
        r'\bluong sau khi ra truong\b',
        r'\bluong.*sau\s*\d+\s*nam\b',
        r'\bthu nhap\b.*(bao nhieu|trung binh|toi thieu|cao nghe nghiep)',
        r'\bluong\b.*(ky su|cu nhan|nhan vien)',
    ],
    'co_hoi_viec_lam': [
        r'\bde xin viec\b',
        r'\bkho xin viec\b',
        r'\bco hoi viec lam\b',
        r'\btrien vong viec lam\b',
        r'\btrien vong nghe nghiep\b',
        r'\bviec lam sau tot nghiep\b',
        r'\bdi lam\b.*(trai nganh|ngoai nganh)',
        # Loại bỏ "nhu cầu tuyển dụng/nhân lực" vì ID=304 là in-scope (Sở giới thiệu nhu cầu nhân lực)
    ],
    'so_sanh_hoac_hoi_truong_khac': [
        r'\bso sanh\b.*(truong|dai hoc)',
        r'\bso voi truong\b',
        r'\btruong nao\b.*(day tot|tot hon|nhieu nganh)',
        r'\bnhieu truong\b',
        r'\bhoc phi truong khac\b',
        r'\bthong tin truong khac\b',
    ] + OTHER_SCHOOLS,
    'ty_le_choi': [
        r'\bty le choi\b',
        r'\bty le do\b',
        r'\bty le trung tuyen\b.*(bao nhieu|nam nay)',
        r'\bbao nhieu nguoi\b.*(nop|dang ky).*nganh',
    ],
    'thong_tin_ca_nhan_bao_mat': [
        r'\bso tai khoan\b.*(ca nhan|cua\s*(?:toi|em|ban|minh))',
        r'\bso the ngan hang\b',
        r'\bso dien thoai\b.*(ca nhan|di dong).*(giang vien|thay|co)',
        r'\bsdt cua\b.*(giang vien|thay|co|ong|ba|truong phong)',
        r'\bzalo cua\b.*(giang vien|thay|co|khoa)',
        r'\bdanh sach\b.*(giang vien|thi sinh|cham thi|noi bo)',
        r'\btra cuu\b.*(so bao danh|sbd)',
        r'\btra cuu\b.*\bdiem\b.*(ban|nguoi|so bao danh|cua em|cua toi|ca nhan)',
        r'\bly lich\b.*(ca nhan)',
        r'\bdiem ren luyen\b',
    ],
    'thong_tin_chua_cong_bo': [
        r'\bda co bao nhieu\b.*(nop ho so|dang ky)',
        r'\bco ai trung tuyen\b',
        r'\bthong ke\b.*(ho so|gioi tinh)',
        r'\bbao nhieu nguoi\b.*(nop|dang ky).*(dot|thang)',
    ],
    'xin_tai_lieu_noi_bo': [
        r'\bxin\b.*(tai lieu|file|de thi).*(noi bo|on thi)',
        r'\bbo de thi\b',
        r'\bgui.*file\b.*(tai lieu)',
        r'\bcho\b.*(file|tai lieu).*(noi bo|cac nam truoc|truong)',
    ],
    'danh_gia_nhan_xet_ca_nhan': [
        r'\bnhan xet\b.*(truong|nganh|de thi|giang vien)',
        r'\breview\b.*(truong|nganh|ktx|ky tuc xa|giang vien|thay|co)',
        r'\breview\s+uth\b',
        r'\bdanh gia\b.*(de thi|gia tri|giang vien|chat luong truong)',
        r'\bco kho tinh\b',
        r'\bxuong cap\b',
        r'\bde thi.*kho\b.*nam nay',
        r'\bhien trang\b.*(co so vat chat|truong)',
    ],
    'tu_van_ca_nhan_suc_khoe_tinh_cach': [
        r'\bem la nguoi\b.*(huong noi|ngoai huong|nhat)',
        r'\bcay say song\b',
        r'\bsay song\b.*(lam|nganh)',
        r'\bco so code\b',
        r'\bnhat\b.*(chon nganh|hoc nganh)',
    ],
    'cam_ket_dam_bao': [
        r'\bdam bao\b.*(100%|viec lam|xin duoc)',
        r'\bchac suat\b.*(vao lam|xin viec)',
        r'\bcam ket\b.*(viec lam|tuyen dung|xin duoc)',
    ],
    'du_doan_tuong_lai_nganh': [
        r'\btuong lai.*nganh\b',
        r'\bnganh.*hot\b',
        r'\b\d+\s*nam toi\b.*nganh',
        r'\bnganh.*xu huong\b',
    ],
    'chuyen_truong': [
        r'\bchuyen truong\b',
        r'\bduoc chuyen\b.*(qua|sang).*(uth|truong)',
    ],
    'hoi_truong_khac_same_city': [
        r'\bngoai\b.*(uth|truong minh|truong nay).*(truong nao|co truong)',
        r'\bcac truong\b.*day.*nganh',
    ],
    'du_doan_diem_san': [
        r'\bdiem san\b.*(nam nay|2026|bao nhieu)',
        r'\blay diem san\b',
    ],
    'nam_tuong_lai': [
        r'\bnam\s*202[7-9]\b',
        r'\bnam\s*20[3-9]\d\b',
    ],
}

def normalize(s: str) -> str:
    """Chuẩn hóa chuỗi tiếng Việt về dạng không dấu, viết thường."""
    s = str(s).lower()
    s = s.replace('đ', 'd').replace('Đ', 'd')
    s = unicodedata.normalize('NFD', s)
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return s

def check_oos(query: str) -> tuple[bool, list[str]]:
    """
    Kiểm tra câu hỏi có nằm ngoài phạm vi tuyển sinh (OOS) hay không.
    Trả về: (is_oos, matched_categories)
    """
    q = normalize(query)
    
    # --- XỬ LÝ NGOẠI LỆ (Exceptions) ---
    # 1. Nếu câu hỏi liên quan đến Thạc sĩ / Tiến sĩ / Sau đại học -> không chặn "tỷ lệ chọi" hay "số tài khoản đóng lệ phí"
    is_postgrad = any(x in q for x in ["thac si", "tien si", "sau dai hoc"])
    
    matched_categories = []
    for category, patterns in PATTERNS.items():
        # Bỏ qua check tỷ lệ chọi cho thạc sĩ/tiến sĩ
        if category == 'ty_le_choi' and is_postgrad:
            continue
            
        for pattern in patterns:
            if re.search(pattern, q):
                matched_categories.append(category)
                break  # Khớp một pattern của nhóm là đủ
                
    return len(matched_categories) > 0, matched_categories
