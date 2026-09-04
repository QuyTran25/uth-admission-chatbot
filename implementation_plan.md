# Kế hoạch Tuần 6 — Song song Backend & Frontend (Bản Final)

Bản kế hoạch đã được hoàn thiện 100% sau khi bổ sung các chốt chặn kỹ thuật: dotenv_path tường minh (tránh regression), nguyên tắc tính điểm gate cho Fuzzy Match (giữ chất lượng dữ liệu tuyển sinh), schema chuẩn cho mock data, và VITE_API_BASE_URL cho Frontend.

---

## 🎯 Chốt Thiết Kế & Quy Tắc Hệ Thống

1. **Lịch sử hội thoại (localStorage vs Server-side History):**
   - **Chốt chọn:** Dùng `localStorage` cho phạm vi Tuần 6 để tập trung hoàn thiện luồng RAG và UI core. Giữ interface quản lý state sạch để chuyển sang Server-side API ở các tuần sau.
2. **Attribution Gate Threshold & Fuzzy Match Rule (A3):**
   - **Chốt chọn quy tắc nghiêm ngặt cho Chatbot Tuyển sinh:**
     - Fuzzy match **KHÔNG được tính là hợp lệ (tính là FAIL / 0.0 điểm)** khi tính `citation_precision`. Nếu `citation_precision < 0.9` ➔ Gate từ chối/cảnh báo câu trả lời.
     - Fuzzy match **CHỈ được ghi log `[HALLUCINATED_ID_WARNING]`** nhằm mục đích debug và tinh chỉnh prompt A1.
     - *Lý do:* Chatbot tuyển sinh (điểm chuẩn, học phí) đòi hỏi độ chính xác tuyệt đối, thà từ chối trích dẫn mập mờ còn hơn đưa thông tin sai nguồn.

---

## 👤 Người A — Backend (Gates / Generator / Config)

> **Thứ tự thực hiện:** A0 (5p) ➔ A2 ➔ A1 (Timebox 2h) ➔ A3.

### A0. Cấu hình CORSMiddleware (5 phút - Bắt buộc làm đầu tiên)
* **Input:** [`main.py`](file:///d:/uth-admission-chatbot/backend/app/main.py)
* **Xử lý:** Kiểm tra/bật `CORSMiddleware` với `allow_origins=["http://localhost:5173", "http://localhost:3000"]`, `allow_credentials=True`, `allow_methods=["*"]`, `allow_headers=["*"]`.
* **Output:** Frontend gửi request không bị lỗi CORS preflight.

---

### A2. Fix config loading — `dotenv_path` tường minh (Tránh lỗi CWD)
* **Input:** [`main.py`](file:///d:/uth-admission-chatbot/backend/app/main.py), [`.env`](file:///d:/uth-admission-chatbot/.env), [`config.py`](file:///d:/uth-admission-chatbot/backend/app/core/config.py)
* **Xử lý:** Dùng đường dẫn tường minh tính từ vị trí file [`main.py`](file:///d:/uth-admission-chatbot/backend/app/main.py):
  ```python
  from pathlib import Path
  from dotenv import load_dotenv

  env_path = Path(__file__).resolve().parents[2] / ".env"
  load_dotenv(dotenv_path=env_path)
  ```
* **Output:** Backend nhận tự động `GEMINI_API_KEY` dù khởi chạy `uvicorn` từ bất kỳ working directory nào.

---

### A1. Prompt Gemini trích dẫn `[[chunk_id]]` (Timebox 2h + Batch Test 5-10 câu)
* **Input:** [`generator.py`](file:///d:/uth-admission-chatbot/backend/app/services/generator.py), [`test_questions_locked.csv`](file:///d:/uth-admission-chatbot/backend/data/test/test_questions_locked.csv)
* **Xử lý Prompt:**
  1. Đưa quy tắc trích dẫn lên **đầu prompt** (dùng UPPERCASE).
  2. Thêm **Few-shot examples**: ví dụ `"Điểm chuẩn ngành Logistics năm 2025 là 18.5 [[2025_diem-chuan_logistics_r001]]."`
  3. Liệt kê danh sách các `chunk_id` hợp lệ sẵn trong context block.
* **Timebox & Mock Fallback Mechanism (nếu quá 2 tiếng chưa xong):**
  - Nếu sau 2h thử prompt Gemini vẫn chưa trích dẫn ổn định: Tạm thời trả dữ liệu response mock với citations giả nhưng **phải đúng Schema thật**:
    ```json
    "citations": [
      {
        "chunk_id": "2025_diem-chuan_logistics_r001",
        "source_file": "2025_diem-chuan.pdf",
        "section_name": "Điểm chuẩn ngành Logistics",
        "admission_year": 2025,
        "source_urls": ["https://example.com/doc.pdf"]
      }
    ]
    ```
  - Mục đích: Người B dùng mock data chuẩn để dựng B5/B2 mà không phải sửa lại code khi chuyển sang data thật.
* **Quy trình Kiểm thử Batch (trước khi Revert DEV MODE):**
  - Chạy thử prompt mới trên **5–10 câu mẫu** từ [`test_questions_locked.csv`](file:///d:/uth-admission-chatbot/backend/data/test/test_questions_locked.csv).
  - Chỉ khi cả 5-10 câu đều trả `citations` đúng schema và không rỗng ➔ mới tiến hành revert DEV MODE bypass trong [`attribution_gate.py`](file:///d:/uth-admission-chatbot/backend/app/services/attribution_gate.py).
* **Sync Point:** Báo ngay cho Người B sau khi A1 pass batch test hoặc khi kích hoạt mock response cho B.

---

### A3. Attribution Gate — Fuzzy matching & Strict Precision Gate
* **Input:** [`attribution_gate.py`](file:///d:/uth-admission-chatbot/backend/app/services/attribution_gate.py)
* **Xử lý Logic:**
  - So sánh `cited_ids` với `retrieved_ids`.
  - Nếu `cid not in retrieved_ids`: Thử fuzzy match (prefix/suffix/normalized ID).
  - **Quy tắc phân loại:**
    - Fuzzy match match được ➔ Ghi log explicit `[HALLUCINATED_ID_WARNING]` (chỉ để debug prompt A1).
    - Về mặt tính điểm: Fuzzy match **tính là INVALID (0.0 điểm)** trong công thức `citation_precision = valid_citations / total_citations`.
    - Nếu `citation_precision < 0.9` (hoặc ratio vi phạm) ➔ Gate kích hoạt hành vi `refused` hoặc `fallback_warning`.
* **Output:** Bảo vệ tối đa độ chính xác của trích dẫn dữ liệu tuyển sinh, đồng thời giúp theo dõi lỗi hallucinate qua log.

---

## 👤 Người B — Frontend (Chat UI / State / Rendering)

> **Thứ tự thực hiện:** B1 ➔ B4 ➔ B3 ➔ *(Task dự phòng nếu A trễ)* ➔ Sync Point ➔ B5 ➔ B2.

### B1. Kết nối Chat UI với API `/api/v1/chat`
* **Input:** [`ChatDetail.jsx`](file:///d:/uth-admission-chatbot/frontend/src/ChatDetail.jsx)
* **Xử lý Environment variable:**
  - Dùng `const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';`
  - Thêm file [`frontend/.env`](file:///d:/uth-admission-chatbot/frontend/.env) có nội dung `VITE_API_BASE_URL=http://localhost:8000`.
* **Xử lý Chat logic:** State `messages[]`, `isLoading`, `error`. Axio POST tới `${API_BASE_URL}/api/v1/chat`. Enter/Send button, Spinner loading và Error Toast.
* **Output:** Chat kết nối backend mượt mà, sẵn sàng cấu hình môi trường deploy về sau.

---

### B4. Kết nối Prompt Chips với Chat Input
* **Input:** Chips trong [`ChatDetail.jsx`](file:///d:/uth-admission-chatbot/frontend/src/ChatDetail.jsx)
* **Xử lý:** `onClick` chip ➔ gọi `sendMessage(chipText)`.
* **Output:** Click chip gửi câu hỏi lập tức.

---

### B3. Lịch sử hội thoại (localStorage)
* **Input:** `messages[]`, `localStorage`
* **Xử lý:** `useEffect` lưu `chat_history`. Đọc `localStorage` khi mount. Nút "Cuộc trò chuyện mới" reset state + xóa storage.
* **Output:** F5 không mất chat, New Chat xóa sạch.

---

### 🎨 Task Dự Phòng cho Người B (Nếu Người A bị trễ A1/A3)
1. **Loading Skeleton Screen:** Dựng hiệu ứng skeleton mượt mà khi chờ response.
2. **Responsive & Mobile View:** Tối ưu sidebar và layout chat cho điện thoại/tablet.
3. **UI Polish & Animations:** Auto-scroll xuống tin nhắn mới, hiệu ứng gõ phím.

---

### B5. Rendering 4 loại `behavior` (Làm sau Sync Point)
* **Input:** `behavior` (`answer`, `fallback_warning`, `refused`, `clarify`), `answer`, `refused_reason`, `year_used`.
* **Xử lý:** Component `<BotMessage>` phân nhánh render:
  - `answer`: Chat bubble chuẩn.
  - `fallback_warning`: Chat bubble + Banner vàng ⚠️ "Dữ liệu năm X chưa có, hiển thị năm gần nhất Y".
  - `refused`: Icon ❌ + Lý do từ chối thân thiện.
  - `clarify`: Hiển thị tin nhắn yêu cầu làm rõ câu hỏi.

---

### B2. Hiển thị Citations — Nguồn tham khảo (Làm sau Sync Point)
* **Input:** `citations[]` (`chunk_id`, `source_file`, `section_name`, `admission_year`, `source_urls[]`).
* **Xử lý:** Component `<CitationBadges>` render danh sách badge nguồn tham khảo. Click badge mở link tab mới hoặc hiển thị tooltip thông tin chi tiết.

---

## 🔄 Timeline Song Song & Sync Point

```
Người A:  [A0]─[A2]───[A1 (Timebox 2h)]────────────────[A3]
                           │
                     (Sync Point / Mock Data)
                           │
Người B:  [B1]──[B4]──[B3]──(Task dự phòng UI nếu A trễ)──[B5]──[B2]
                           │
                           └──────────────────────────────────────┐
                                                                  ▼
Kiểm thử tích hợp End-to-End cuối tuần (30-60 phút):  [E2E Testing Session]
```

---

## 🧪 Bước Tích Hợp Cuối Tuần: E2E Integration Testing (30–60 phút)

1. **Chuẩn bị câu hỏi test cho 4 trạng thái:**
   - **`answer`**: *"Điểm chuẩn ngành Công nghệ thông tin năm 2024 là bao nhiêu?"*
   - **`fallback_warning`**: *"Điểm chuẩn ngành Logistics năm 2026?"* (fallback 2025).
   - **`refused`**: *"Cho tôi công thức chế tạo thuốc nổ"* (out of scope).
   - **`clarify`**: *"Học phí thế nào?"* (câu hỏi mơ hồ).
2. **Nội dung kiểm tra:**
   - UI render đúng màu/icon/banner cho 4 `behavior`.
   - Badge Citations hiển thị đúng thông tin trích dẫn thật.
   - `localStorage` lưu đúng dữ liệu.
   - Rà soát log Backend xem có `[HALLUCINATED_ID_WARNING]` nào xuất hiện trong A3 không.

---

## 📂 Summary các File thay đổi

### Backend
- [MODIFY] [`main.py`](file:///d:/uth-admission-chatbot/backend/app/main.py) (A0: CORSMiddleware, A2: `dotenv_path=Path(__file__).resolve().parents[2] / ".env"`)
- [MODIFY] [`generator.py`](file:///d:/uth-admission-chatbot/backend/app/services/generator.py) (A1: Prompt tuning, few-shots & mock schema chuẩn)
- [MODIFY] [`attribution_gate.py`](file:///d:/uth-admission-chatbot/backend/app/services/attribution_gate.py) (A1: Revert bypass sau batch test; A3: Fuzzy match counts FAIL for precision + log warning)

### Frontend
- [NEW] [`frontend/.env`](file:///d:/uth-admission-chatbot/frontend/.env) (`VITE_API_BASE_URL=http://localhost:8000`)
- [MODIFY] [`ChatDetail.jsx`](file:///d:/uth-admission-chatbot/frontend/src/ChatDetail.jsx) (B1, B4, B3: `import.meta.env.VITE_API_BASE_URL`, Axios API, Chips, LocalStorage)
- [NEW] `frontend/src/components/BotMessage.jsx` (B5: Render 4 loại behavior)
- [NEW] `frontend/src/components/CitationBadges.jsx` (B2: Render danh sách nguồn trích dẫn)
