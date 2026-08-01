# ĐỀ CƯƠNG THỰC TẬP TỐT NGHIỆP

**ĐH Giao thông Vận tải TP.HCM**
**GVHD: ThS. Nguyễn Thanh Tiến**

## Thông tin chung

**Tên đề tài:** Chatbot hỗ trợ tư vấn tuyển sinh Trường Đại học Giao thông Vận tải Thành phố Hồ Chí Minh.

**Sinh viên thực hiện:**

- Huỳnh Thị Quý Trân – MSSV 051305000763
- Nguyễn Đỗ Anh Khoa – MSSV 077205005875

**Giảng viên hướng dẫn:** ThS. Nguyễn Thanh Tiến.

**Phân công dự kiến:**

| Thành viên | Nhiệm vụ |
|---|---|
| Huỳnh Thị Quý Trân | - Thu thập, tiền xử lý dữ liệu tuyển sinh (PDF/Website → Markdown, chuẩn hóa, gắn metadata) và xây dựng quy trình 6 bước xử lý bảng<br>- Xây dựng Knowledge Base, Embedding, lập chỉ mục FAISS/BM25<br>- Triển khai Retrieval API (FastAPI) và bàn giao endpoint theo API contract; xây dựng Hybrid Retrieval (BM25 + Vector)<br>- Xây dựng cơ chế kiểm soát năm tuyển sinh trong tầng truy vấn<br>- Xây dựng và hiệu chỉnh Retrieval Gate (lớp từ chối 1) |
| Nguyễn Đỗ Anh Khoa | - Xây dựng mock retrieval API theo đúng API contract đã chốt (Tuần 1), làm nền phát triển Generation/Frontend độc lập<br>- Phát triển Backend cho tầng Generation (FastAPI), tích hợp Gemini API, xây dựng Prompt Builder<br>- Xây dựng Attribution Gate và kiểm tra độc lập câu trả lời theo chunk truy xuất<br>- Xây dựng Conversation Memory (mở rộng nếu còn thời gian)<br>- Thiết kế và phát triển giao diện Web (React), Chat UI, hiển thị trích dẫn nguồn và lịch sử hội thoại<br>- Thay mock bằng Retrieval API thật khi được bàn giao, kiểm thử tích hợp Backend–Frontend |
| Cả 2 | - Phụ trách tổ chức đánh giá và tổng hợp kết quả thực nghiệm |

*Phân công chi tiết của Cả 2:*

- Khảo sát, thiết kế kiến trúc hệ thống; chốt API contract giữa retrieval – generation ngay Tuần 1
- Cùng xây dựng bộ câu hỏi kiểm thử và gán nhãn (dựa trên hiểu biết dữ liệu tuyển sinh của cả hai)
- Cùng thực hiện thực nghiệm so sánh cấu hình truy xuất (BM25/Vector/Hybrid) và phân tích kết quả
- Kiểm thử tích hợp toàn hệ thống, phân tích kết quả thực nghiệm
- Viết báo cáo và chuẩn bị bảo vệ

---

## 1. Đặt vấn đề

Trong mỗi kỳ tuyển sinh, thí sinh và phụ huynh thường xuyên có nhu cầu tra cứu thông tin về phương thức xét tuyển, điểm chuẩn, chỉ tiêu và học phí. Các thông tin này nằm rải rác trên website và trong đề án tuyển sinh, khiến việc tra cứu thủ công mất thời gian và dễ nhầm lẫn. Một công cụ hỏi đáp tự động, có khả năng xử lý tốt dữ liệu và trả lời kèm trích dẫn nguồn rõ ràng, sẽ giúp người dùng tra cứu nhanh chóng và chính xác, đồng thời giảm tải cho bộ phận tư vấn tuyển sinh của trường.

---

## 2. Mục tiêu và phạm vi

### Mục tiêu:

**(1)** Xây dựng chatbot trả lời câu hỏi tuyển sinh dựa trên văn bản chính thức của trường, đạt Answer Accuracy ≥85% trên bộ câu hỏi kiểm thử có đáp án tham chiếu. Đối với các câu trả lời mở (không thể so khớp tự động với đáp án tham chiếu), LLM-as-a-judge chỉ đóng vai trò hỗ trợ chấm sơ bộ; kết quả cuối cùng do người chấm (nhóm thực hiện) rà soát và quyết định, LLM-as-a-judge không thay thế người chấm.

**(2)** Mỗi câu trả lời kèm trích dẫn nguồn (tên tài liệu, trang, mục), đạt Citation Precision ≥ 90% trên bộ câu hỏi kiểm thử, đánh giá độc lập với cơ chế Attribution Gate của hệ thống.

**(3)** Hệ thống nhận biết và từ chối các câu hỏi nằm ngoài phạm vi hoặc yêu cầu dự đoán, đạt đồng thời Refusal Recall ≥90% và Over-refusal Rate ≤10% trên bộ câu hỏi kiểm thử.

### Phạm vi:

**Chatbot hỗ trợ**

**Thông tin tuyển sinh**

- Phương thức xét tuyển (năm 2026)
- Điều kiện xét tuyển (năm 2026)
- Chỉ tiêu (năm 2026)
- Ngành đào tạo (2026)
- Điểm chuẩn (2022, 2023, 2024, 2025, 2026)

**Thông tin học tập**

- Học phí (2026)
- Học bổng (2026)
- Chương trình đào tạo (2026)

**Thông tin nhập học**

- Hồ sơ (2026)
- Thời gian (2026)
- Quy định nhập học (2026)

**Thông tin trường**

- Địa chỉ (2026)
- Cơ sở (2026)
- Liên hệ (2026)

**Ngoài phạm vi: Chatbot từ chối và không bịa câu trả lời:**

- Dự đoán điểm chuẩn
- Tư vấn chọn ngành
- Cơ hội việc làm
- Lương sau tốt nghiệp
- So sánh trường
- Thông tin chưa công bố

### 2.1. Kiểm soát năm tuyển sinh trong dữ liệu

Đề tài hướng đến kỳ tuyển sinh năm 2026. Tuy nhiên tại thời điểm thực hiện đồ án, một số thông tin năm 2026 (ví dụ điểm chuẩn) có thể chưa được trường công bố chính thức. Nếu không kiểm soát, hệ thống có thể trả lời sai năm mà không báo cho người dùng biết. Nhóm xây dựng cơ chế kiểm soát năm tuyển sinh như sau.

**Phương án – Gắn metadata năm tuyển sinh và ưu tiên truy xuất theo năm:**

- **Phạm vi dữ liệu:** Knowledge Base lưu trữ tài liệu tuyển sinh năm 2025 và 2026, mỗi chunk được gắn metadata admission_year.
- **Tiền xử lý:** mỗi chunk được gắn metadata admission_year, document_type, table_id, page,...; nếu bảng gốc chứa dữ liệu nhiều năm trong cùng cấu trúc, từng dòng/cột được tách thành chunk riêng và gắn đúng admission_year tương ứng trước khi lập chỉ mục.
- **Xử lý truy vấn:**
  - Nếu câu trả lời đã có dữ liệu chính thức năm 2026 (áp dụng cho hầu hết các loại thông tin), hệ thống trả lời kèm ghi rõ nguồn năm, theo mẫu: "Theo thông tin [tên mục] năm 2026, ...".
  - Riêng đối với điểm chuẩn (loại thông tin duy nhất có nhiều năm dữ liệu):
    - Nếu người dùng hỏi điểm chuẩn không nêu rõ năm, hệ thống mặc định trả lời theo năm 2026 nếu đã có; nếu năm 2026 chưa công bố, hệ thống báo rõ "hiện tại chưa có thông tin điểm chuẩn năm 2026", sau đó cung cấp điểm chuẩn các năm 2023, 2024, 2025 (và 2022 nếu liên quan) làm thông tin tham khảo, đồng thời lưu ý rõ: "Từ năm 2025 trường đã thay đổi cách tính điểm chuẩn"; hệ thống có thể gợi ý người dùng nhập điểm của mình để được hỗ trợ tra cứu/quy đổi phù hợp.
    - Nếu người dùng chỉ rõ năm cụ thể (ví dụ: "điểm chuẩn năm 2023"), hệ thống chỉ truy xuất và trả lời theo đúng năm đó.
    - Nếu người dùng hỏi năm không có trong Knowledge Base (trước 2022), hệ thống thông báo không có dữ liệu thay vì trả lời hoặc bỏ trống câu trả lời.
  - Ở mọi trường hợp, hệ thống không gộp lẫn dữ liệu của các năm khác nhau trong cùng một câu trả lời mà không ghi rõ năm tương ứng, tránh gây hiểu nhầm dữ liệu năm này là của năm khác

### 2.2. Cơ chế từ chối hai lớp

**Lớp 1 – Retrieval Gate (trước khi gọi LLM):**

- Sau Hybrid Retrieval, hệ thống không chỉ dựa vào retrieval score của kết quả xếp hạng cao nhất (top-1), mà kết hợp thêm tín hiệu khác để quyết định, ví dụ: khoảng cách điểm giữa top-1 và top-2 (score margin), độ đồng thuận giữa BM25 và dense trong top-k, hoặc điểm trung bình của top-k kết quả liên quan.
- Ngưỡng từ chối được hiệu chỉnh trên tập câu hỏi có nhãn (trong phạm vi/ngoài phạm vi), theo hướng selective prediction; phương pháp hiệu chỉnh tham khảo hướng conformal prediction của CONFLARE [8].
- Nếu tổ hợp tín hiệu trên không đạt ngưỡng, hệ thống dừng tại tầng retrieval, không gọi LLM và trả về thông báo ngoài phạm vi.

**Lớp 2 – Attribution Gate (sau khi sinh):**

- Các chunk truy xuất mang sẵn chunk_id/table_id; prompt yêu cầu LLM trả lời kèm định danh của các chunk đã truy xuất.
- Hệ thống kiểm tra độc lập, không phụ thuộc LLM: nguồn trích dẫn có tồn tại và nội dung có được chunk hỗ trợ, triển khai theo hai mức:
  - **Bắt buộc:** đối chiếu trực tiếp cặp header–giá trị đối với dữ liệu bảng (điểm chuẩn, học phí, chỉ tiêu...), bao phủ phần lớn câu hỏi tuyển sinh, không cần thêm mô hình.
  - **Định hướng mở rộng:** sử dụng mô hình fact-checking độc lập (MiniCheck [9] là phương án tham khảo) đối với văn bản tự do (quy định, chính sách).
- Nếu không vượt qua bước kiểm tra, hệ thống không xuất câu trả lời và trả về thông báo từ chối hoặc yêu cầu làm rõ.

### 2.3. Sản phẩm đầu ra dự kiến

- Corpus tuyển sinh 2025–2026 từng nguồn chính thức.
- Dữ liệu bảng dạng structured records và retrieval text.
- BM25, dense, hybrid retrieval.
- Metadata theo năm, loại tài liệu, trang/mục.
- Backend retrieval/generation, web UI và data validation report.
- Dev/test, gold evidence và báo cáo metric.

---

## 3. Khảo sát công trình liên quan

Đề tài dựa trên ba hướng nghiên cứu:

- **Kiến trúc RAG và hybrid retrieval:** kết hợp LLM với tri thức ngoài để trả lời có căn cứ [1]; hybrid retrieval (BM25 + dense) là baseline phổ biến từ 2024.
- **Xử lý dữ liệu bảng cho RAG:** trích xuất bảng có cấu trúc từ tài liệu [2], [3]; hỏi-đáp và chunking trên dữ liệu bảng [4], [5], [6]; liên kết bản ghi giữa các bảng [7].
- **Kiểm soát câu trả lời sai:** hiệu chỉnh ngưỡng từ chối bằng conformal prediction [8]; fact-checking độc lập đối chiếu câu trả lời với ngữ cảnh truy xuất [9].

**Kế thừa:** đề tài dùng các kỹ thuật trên làm nền cho quy trình trích xuất–chunking bảng (Mục 5.1) và cơ chế từ chối hai lớp (Mục 2.2).

**Khoảng trống:** các công trình trên xử lý bảng đơn lẻ, tổng quát, chưa giải quyết đồng thời các tình huống của bảng tuyển sinh — bảng cắt qua trang, chú thích ký hiệu, ô merge nhiều tầng, thực thể rải ở nhiều bảng, và biến động dữ liệu theo năm tuyển sinh — đây là phần đề tài bổ sung.

---

## 4. Nội dung thực hiện dự kiến

- Thu thập và tiền xử lý dữ liệu tuyển sinh từ các nguồn chính thức của trường (đề án tuyển sinh, website, FAQ, học phí, chương trình đào tạo); chuẩn hóa dữ liệu và gắn metadata.
- Xây dựng hệ thống truy xuất thông tin dựa trên kiến trúc RAG, sử dụng Hybrid Retrieval để tìm kiếm các đoạn văn bản liên quan đến câu hỏi.
- Xây dựng chức năng sinh câu trả lời bằng LLM, kèm theo trích dẫn nguồn (tên tài liệu, mục hoặc trang).
- Xây dựng cơ chế từ chối các câu hỏi ngoài phạm vi hoặc yêu cầu dự đoán.
- Xây dựng giao diện web cho phép người dùng hỏi đáp và xem nguồn tham khảo của câu trả lời.
- Kiểm thử và đánh giá hệ thống trên bộ câu hỏi tuyển sinh.

---

## 5. Phương pháp và công nghệ dự kiến

- **Phương pháp:** Áp dụng kiến trúc Retrieval-Augmented Generation (RAG) kết hợp Hybrid Retrieval (Dense Retrieval và Sparse Retrieval) để truy xuất và sinh câu trả lời dựa trên cơ sở tri thức tuyển sinh.
- **Công nghệ dự kiến:** Python (FastAPI) cho Backend, React cho Frontend; mô hình Embedding thuộc thư viện Sentence-Transformers; cơ sở dữ liệu vector FAISS kết hợp BM25 (rank_bm25); Google Gemini API cho mô hình ngôn ngữ lớn (LLM).
- **Đánh giá:** Sử dụng bộ câu hỏi kiểm thử để đánh giá Precision@k của bước truy xuất, độ chính xác của câu trả lời và khả năng trích dẫn đúng nguồn tham khảo.

### 5.1. Tiêu chí đầu ra và quy trình xử lý dữ liệu bảng

Dữ liệu tuyển sinh (điểm chuẩn, chỉ tiêu, học phí) chủ yếu ở dạng bảng nhiều cột; chunking theo ký tự sẽ cắt mất dòng tiêu đề và làm chunk mất ngữ cảnh. Nhóm bổ sung 4 tiêu chí đầu ra và quy trình 7 bước sau.

Quy trình xử lý bảng là bán tự động: các bước dùng công cụ/mô hình để xử lý tự động, nhưng có bước kiểm tra thủ công (spot-check đối chiếu chunk sinh ra với tài liệu gốc) trước khi đưa vào lập chỉ mục, nhằm đảm bảo độ chính xác của dữ liệu tuyển sinh.

**Tiêu chí đầu ra của một chunk:**

- **Tự chứa ngữ nghĩa (Self-contained):** chunk không phụ thuộc chunk khác để hiểu đúng ý nghĩa.
- **Bảo toàn quan hệ bảng (Structure-preserving):** giữ đúng cặp header – giá trị của từng ô.
- **Diễn giải tự nhiên (LLM-readable):** câu văn mạch lạc (fluency), trung thực với dữ liệu gốc, không suy diễn thêm (faithfulness).
- **Có thể truy xuất được (Retrievable):** chứa đủ thực thể/từ khóa (ngành, mã ngành, phương thức, năm) để khớp câu hỏi thực tế của thí sinh.

**Quy trình xử lý:**

**Bước 1 – Layout Analysis & Reading Order Recovery:**

- **Output:** văn bản + bảng theo đúng thứ tự đọc, dạng JSON có cấu trúc (DoclingDocument) — mỗi bảng đã được tách sẵn thành TableItem riêng biệt kèm row_span/col_span
- **Công cụ:** Docling – DocLayNet + TableFormer [2].
- **Trọng tâm:** tránh OCR lẫn cột khi ảnh chụp/scan.

**Bước 2 – Ghép bảng bị cắt qua trang:**

- **Output:** bảng logic duy nhất, không còn bịchia đôi do ranh giới trang.
- **Trọng tâm:** không tách chú thích khỏi bảng gốc.

**Bước 3 – Gán bảng vào mục ngữ nghĩa (Table-to-Section Assignment)**

- **Output:** mỗi TableItem (đã được Docling tách sẵn từ Bước 1) được gán 1 table_id kèm tên mục ngữ nghĩa tương ứng (ví dụ: "II. Điểm chuẩn", "IV. Học phí"), dựa trên heading gần nhất phía trước.
- **Căn cứ:** Cấu trúc bảng được bảo toàn từ Docling; heading được xác định theo quan hệ vị trí trong tài liệu.
- **Trọng tâm:** không gộp các bảng khác schema.

**Bước 4 – Resolve chú thích:**

- **Output:** ô dữ liệu đã thay ký hiệu (*, **, ***) bằng nội dung đầy đủ; annotation "Ghi chú:" cấp bảng được gắn sẵn để chèn vào cuối mỗi chunk liên quan.
- **Trọng tâm:** không còn ký hiệu trơ nghĩa trong ô.

**Bước 5 – Segment-header & Paste-down:**

- **Output:** mỗi dòng dữ liệu đã gắn segment_context và có đủ giá trị ở ô bị merge dọc (chỉ paste-down cho ô dữ liệu, không cho ô header).
- **Căn cứ:** tài liệu kỹ thuật của Docling xác nhận JSON output có sẵn row_span/col_span cho ô merge, nhưng không có tùy chọn tự động lan giá trị (value propagation) cho ô multi-span — paste-down là khoảng trống thật giữa công cụ có sẵn và bài toán, phải xử lý thủ công ở tầng ứng dụng.
- **Trọng tâm:** không mất ngữ cảnh nhóm/campus.

**Bước 6 – Cây header phân cấp + Row-level KV Chunking (cốt lõi):**

- **Output:** 1 chunk tự chứa cho mỗi dòng dữ liệu, dạng "[Tên bảng – ngữ cảnh]. [Header 1]: giá trị1. …", dựng từ full header path của ô merge ngang.
- **Căn cứ:** Pal, Kanoulas & de Rijke [4]; Guttal et al. [5].
- **Trọng tâm:** giá trị như "24.5" luôn kèm ngành, phương thức, năm ngay trong chunk.

**Bước 7 – Liên kết bảng chéo (Entity Resolution) – Phần mở rộng**

- **Output:** chunk của bảng phụ (vd. học phí) được bổ sung tên đầy đủ của thực thể liên kết, khớp qua fuzzy matching với bảng chính.
- **Căn cứ:** mô hình Fellegi–Sunter [7].
- **Trọng tâm:** nối đúng thông tin nằm rải ở nhiều bảng.

**Output cuối cùng của toàn bộ pipeline (6 bước trên):** Tập các chunk tự chứa (self-contained chunks), mỗi chunk bảo toàn đầy đủ ngữ cảnh của một dòng dữ liệu bảng (header, nhóm, chú thích và giá trị), sẵn sàng cho bước lập chỉ mục (indexing).

Trong hệ thống chatbot, các chunk này sẽ được đưa vào Hybrid Retrieval (BM25 + Vector, lọc theo metadata; tham khảo kiến trúc tách schema/cell của TableRAG [6]) → Generation (từ chối 2 lớp + kiểm tra trích dẫn).

---

## 6. Kết quả dự kiến

Một chatbot nền web hoạt động ổn định, trả lời đúng phần lớn câu hỏi trong bộ kiểm thử. Mỗi câu trả lời đi kèm trích dẫn nguồn; từ chối chính xác các câu hỏi ngoài phạm vi hoặc yêu cầu dự đoán.

---

## 7. Kế hoạch thực hiện theo tuần

| Tuần | Nội dung công việc dự kiến |
|---|---|
| **Tuần 1** | - Lập kế hoạch, tìm và đọc tài liệu liên quan, làm quen công nghệ<br>- Thu thập tài liệu tuyển sinh từng nguồn chính thức của trường<br>- Xây dựng kiến trúc hệ thống, thiết lập môi trường phát triển<br>- Chốt API contract giữa các thành phần (retrieval, generation, frontend)<br>- Phác thảo khung bộ câu hỏi kiểm thử: danh mục câu hỏi, tiêu chí gán nhãn trong/ngoài phạm vi |
| **Tuần 2** | - Tiền xử lý dữ liệu: chuyển đổi PDF/Website sang Markdown, làm sạch dữ liệu, chuẩn hóa bảng biểu, gắn Metadata<br>- Thực hiện các bước đầu của quy trình xử lý bảng: Layout Analysis, ghép bảng bị cắt qua trang<br>- Mở rộng bộ câu hỏi kiểm thử; bắt đầu gán đáp án tham chiếu<br>- Xây dựng báo cáo kiểm tra chất lượng dữ liệu bước đầu (data validation report) cho corpus mẫu |
| **Tuần 3** | - Hoàn thiện quy trình xử lý bảng cốt lõi (6 bước): gán bảng vào mục ngữ nghĩa, resolve chú thích, paste-down, KV chunking; có bước kiểm tra thủ công đối chiếu với tài liệu gốc. (Liên kết bảng chéo/Entity Resolution để ở phần mở rộng, thực hiện sau nếu còn thời gian.)<br>- Sinh self-contained chunks, tạo Embedding và lập chỉ mục FAISS/BM25<br>- Hoàn thiện bộ câu hỏi kiểm thử: đủ câu trong/ngoài phạm vi, đáp án tham chiếu, nguồn trích dẫn |
| **Tuần 4** | - Phát triển Backend bằng FastAPI, xây dựng Hybrid Retrieval<br>- Thực nghiệm so sánh BM25-only / Vector-only / Hybrid trên bộ câu hỏi kiểm thử (bảng Precision@k, Recall@k) để chọn cấu hình truy xuất<br>- Xây dựng cơ chế kiểm soát năm tuyển sinh trong tầng truy vấn |
| **Tuần 5** | - Tích hợp Gemini API, xây dựng Prompt Builder<br>- Xây dựng và đánh giá cơ chế Retrieval Gate (hiệu chỉnh ngưỡng từ chối) trên bộ câu hỏi có nhãn<br>- Xây dựng cơ chế trích dẫn nguồn (Attribution Gate), đối chiếu header–giá trị cho dữ liệu bảng<br>- Khóa bộ câu hỏi kiểm thử (test set) để chuẩn bị đánh giá ở Tuần 7 |
| **Tuần 6** | - Phát triển giao diện React, tích hợp Chat UI, lịch sử hội thoại, hiển thị trích dẫn nguồn<br>- Kết nối Backend<br>- Kiểm thử tích hợp Backend–Frontend |
| **Tuần 7** | - Tích hợp toàn hệ thống<br>- Đánh giá Answer Accuracy, Citation Precision, Refusal Recall, Over-refusal Rate trên bộ câu hỏi kiểm thử<br>- Tối ưu hệ thống theo kết quả đánh giá |
| **Tuần 8** | - Hoàn thiện hệ thống, sửa lỗi<br>- Viết báo cáo, chuẩn bị slide và bảo vệ |

---

## 8. Tài liệu tham khảo

[1] Y. Gao, Y. Xiong, X. Gao, et al., "Retrieval-Augmented Generation for Large Language Models: A Survey," arXiv preprint, arXiv:2312.10997, 2023.

[2] C. Auer, M. Lysak, A. Nassar, et al., "Docling Technical Report," arXiv preprint, arXiv:2408.09869, 2024.

[3] B. Smock, R. Pesala, R. Abraham, "PubTables-1M: Towards Comprehensive Table Extraction from Unstructured Documents," Proc. IEEE/CVF CVPR, pp. 4634–4642, 2022.

[4] V. Pal, E. Kanoulas, M. de Rijke, "Parameter-Efficient Abstractive Question Answering over Tables or Text," Proc. 2nd DialDoc Workshop, ACL, pp. 41–53, 2022.

[5] P. Guttal, V. Magotra, V. Mahavishnu, et al., "Structure-Aware Chunking for Tabular Data in Retrieval-Augmented Generation," arXiv preprint, arXiv:2605.00318, 2026.

[6] S.-A. Chen, L. Miculicich, J. M. Eisenschlos, et al., "TableRAG: Million-Token Table Understanding with Language Models," Advances in Neural Information Processing Systems (NeurIPS), 2024.

[7] I. P. Fellegi, A. B. Sunter, "A Theory for Record Linkage," Journal of the American Statistical Association, vol. 64, no. 328, pp. 1183–1210, 1969.

[8] P. Rouzrokh, S. Faghani, C. U. Gamble, M. Shariatnia, B. J. Erickson, "CONFLARE: CONFormal LArge language model REtrieval," arXiv preprint, arXiv:2404.04287, 2024.

[9] L. Tang, P. Laban, G. Durrett, "MiniCheck: Efficient Fact-Checking of LLMs on Grounding Documents," Proc. 2024 Conference on Empirical Methods in Natural Language Processing (EMNLP), pp. 8818–8847, 2024.
