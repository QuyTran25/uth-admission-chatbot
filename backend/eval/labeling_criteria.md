# Hướng dẫn Gán nhãn & Bộ Câu hỏi Mẫu (Tuần 2)

Tài liệu này chuẩn hóa tiêu chí phân loại câu hỏi (Trong/Ngoài phạm vi) và danh mục câu hỏi mẫu dưới dạng liệt kê trọng tâm, được phân chia theo hệ thống phân cấp gồm 4 nhóm lớn và 14 nhãn tài liệu (`document_type`) cụ thể làm căn cứ xây dựng bộ dữ liệu kiểm thử.

---

## 1. Tiêu chí Gán nhãn Câu hỏi (Labeling Criteria)

Mỗi câu hỏi đầu vào phải được định nghĩa bằng các trường thông tin sau:
- **`document_type`**: Loại tài liệu đích cần truy xuất (1 trong 14 nhóm cụ thể, được tổ chức theo 4 nhóm lớn):
  * **Nhóm I: Thông tin tuyển sinh**
    - `admission_method` (Phương thức xét tuyển)
    - `admission_condition` (Điều kiện xét tuyển)
    - `admission_quota` (Chỉ tiêu)
    - `program_info` (Ngành đào tạo)
    - `cutoff_score` (Điểm chuẩn)
  * **Nhóm II: Thông tin học tập**
    - `tuition_fee` (Học phí)
    - `scholarship` (Học bổng)
    - `curriculum_info` (Chương trình đào tạo)
  * **Nhóm III: Thông tin nhập học**
    - `admission_profile` (Hồ sơ)
    - `admission_time` (Thời gian)
    - `admission_regulation` (Quy định nhập học)
  * **Nhóm IV: Thông tin trường**
    - `address_info` (Địa chỉ)
    - `campus_info` (Cơ sở)
    - `contact_info` (Liên hệ)
- **`filter_year`**: Năm tuyển sinh cần lọc (chỉ nhận giá trị từ `2022` đến `2026`, hoặc `null` nếu không xác định).
- **`is_in_scope`**: Trạng thái câu hỏi (`true` - trong phạm vi hỗ trợ, `false` - ngoài phạm vi hỗ trợ).
- **`expected_action`**: Hành vi mong đợi của hệ thống (phân tách rõ ràng để phục vụ đánh giá tính đúng đắn ở Tuần 7):
  - `answer_specific_year`: Trả lời trực tiếp dựa trên dữ liệu năm cụ thể được thí sinh nêu rõ trong câu hỏi (áp dụng cho điểm chuẩn các năm 2022-2026 hoặc các thông tin tuyển sinh khác của năm 2026 khi được hỏi cụ thể).
  - `answer_default_2026`: Trả lời dựa trên dữ liệu mặc định năm 2026 khi câu hỏi không chỉ định năm (và hệ thống đã có sẵn dữ liệu năm 2026).
  - `answer_fallback_notice`: Trả lời bằng cách thông báo chưa có dữ liệu 2026 + cung cấp dữ liệu năm cũ (2023–2025 và 2022 nếu liên quan) kèm cảnh báo đổi cách tính điểm tuyển sinh từ 2025 (chỉ áp dụng khi hỏi điểm chuẩn mà chưa có dữ liệu 2026, đồng thời câu hỏi không nêu năm hoặc nêu năm 2026).
  - `refuse`: Từ chối trả lời một cách lịch sự (Out-of-Scope).

### 1.1. Trường hợp Trong phạm vi (In-Scope - `is_in_scope = true`)
- **Nhóm Điểm chuẩn (`cutoff_score`)**:
  - Yêu cầu: Câu hỏi hỏi về điểm trúng tuyển của các ngành học tại UTH.
  - Năm hỗ trợ: Điểm chuẩn hỗ trợ tra cứu trong khoảng từ **2022 đến 2026**.
  - Xử lý hành động (`expected_action`):
    - Nếu thí sinh **nói rõ năm cụ thể** (2022-2026): expected_action là `answer_specific_year` (truy xuất đúng năm được yêu cầu).
    - Nếu thí sinh **không nêu năm**: Hệ thống tự động mặc định chọn năm 2026:
      - Nếu đã có dữ liệu 2026: expected_action là `answer_default_2026` (ghi rõ "Theo thông tin năm 2026...").
      - Nếu chưa có dữ liệu 2026: expected_action là `answer_fallback_notice` (chạy luồng fallback cảnh báo và cung cấp dữ liệu năm cũ).
- **13 nhóm tài liệu còn lại** (Học phí, Hồ sơ, Chỉ tiêu, Địa chỉ...):
  - Yêu cầu: Câu hỏi hỏi về các thông tin tuyển sinh hiện hành tại UTH.
  - Năm hỗ trợ: Chỉ hỗ trợ dữ liệu năm mới nhất **2026**.
  - Xử lý hành động (`expected_action`):
    - Nếu thí sinh **nói rõ năm 2026**: expected_action là `answer_specific_year`.
    - Nếu thí sinh **không nêu năm**: expected_action là `answer_default_2026` (mặc định lấy dữ liệu 2026).
    - Nếu thí sinh **nói rõ năm khác 2026** (2022-2025): expected_action là `refuse` (do các nhóm thông tin này không hỗ trợ năm cũ).

### 1.2. Trường hợp Ngoài phạm vi (Out-of-Scope - `is_in_scope = false`)
- **Dự đoán tương lai**: Hỏi điểm chuẩn hoặc chỉ tiêu của các năm sau 2026 (ví dụ: điểm chuẩn năm 2027) hoặc yêu cầu dự đoán điểm chuẩn năm nay tăng hay giảm.
- **Tư vấn hướng nghiệp**: Yêu cầu lời khuyên chọn ngành, đánh giá cá nhân (ví dụ: nên chọn ngành nào, ngành nào dễ xin việc hơn).
- **So sánh liên trường**: So sánh chất lượng, học phí, cơ sở vật chất của UTH với các trường đại học khác.
- **Thông tin chưa công bố**: Các câu hỏi về lịch học cụ thể, phân lớp học, danh sách giảng viên, lịch thi... (không nằm trong đề án tuyển sinh).
- **Năm tuyển sinh không hỗ trợ**:
  - Hỏi điểm chuẩn các năm trước 2022 (năm < 2022).
  - Hỏi học phí, chỉ tiêu, đề án của các năm cũ từ 2022 đến 2025.
- **Câu hỏi ngoài lề**: Hỏi thời tiết, trò chuyện tự do, các chủ đề không liên quan đến tuyển sinh.

---

## 2. Danh mục Câu hỏi Mẫu theo Nhóm Nghiệp vụ

### Nhóm I: Thông tin tuyển sinh

#### 2.1. Phương thức xét tuyển (`admission_method`) - Hỗ trợ năm 2026
- **Câu hỏi hợp lệ (Trong phạm vi, trả lời trực tiếp)**:
  - "Năm 2026 UTH có những phương thức xét tuyển nào?" (filter_year: 2026, expected_action: answer_specific_year)
  - "Phương thức xét học bạ UTH yêu cầu những gì?" (filter_year: 2026, expected_action: answer_default_2026, tự ngầm định 2026)
- **Câu hỏi không hợp lệ (Ngoài phạm vi, từ chối)**:
  - "Năm 2024 trường xét tuyển học bạ thế nào?" (filter_year: 2024, expected_action: refuse, sai năm hỗ trợ)

#### 2.2. Điều kiện xét tuyển (`admission_condition`) - Hỗ trợ năm 2026
- **Câu hỏi hợp lệ (Trong phạm vi, trả lời trực tiếp)**:
  - "Điều kiện để xét tuyển học bạ vào ngành Logistics năm 2026 là gì?" (filter_year: 2026, expected_action: answer_specific_year)
  - "Học sinh giỏi 3 năm THPT có được ưu tiên xét tuyển thẳng không?" (filter_year: 2026, expected_action: answer_default_2026, tự ngầm định 2026)
- **Câu hỏi không hợp lệ (Ngoài phạm vi, từ chối)**:
  - "Đề thi đánh giá năng lực năm 2024 của trường có khó không?" (filter_year: 2024, expected_action: refuse, sai năm tuyển sinh)

#### 2.3. Chỉ tiêu tuyển sinh (`admission_quota`) - Hỗ trợ năm 2026
- **Câu hỏi hợp lệ (Trong phạm vi, trả lời trực tiếp)**:
  - "Chỉ tiêu tuyển sinh của ngành Công nghệ thông tin năm 2026 là bao nhiêu?" (filter_year: 2026, expected_action: answer_specific_year)
  - "Năm UTH tuyển bao nhiêu chỉ tiêu cho phương thức xét học bạ?" (filter_year: 2026, expected_action: answer_default_2026, tự ngầm định 2026)
- **Câu hỏi không hợp lệ (Ngoài phạm vi, từ chối)**:
  - "Năm ngoái trường tuyển bao nhiêu chỉ tiêu ngành Kỹ thuật ô tô?" (filter_year: 2025, expected_action: refuse, sai năm tuyển sinh)

#### 2.4. Ngành đào tạo (`program_info`) - Hỗ trợ năm 2026
- **Câu hỏi hợp lệ (Trong phạm vi, trả lời trực tiếp)**:
  - "Trường UTH năm 2026 có đào tạo ngành Kỹ thuật ô tô chất lượng cao không?" (filter_year: 2026, expected_action: answer_specific_year)
  - "Mã ngành của Công nghệ thông tin UTH là gì?" (filter_year: 2026, expected_action: answer_default_2026, tự ngầm định 2026)
- **Câu hỏi không hợp lệ (Ngoài phạm vi, từ chối)**:
  - "Ngành nào có cơ hội đi du học Nhật Bản nhiều nhất?" (filter_year: 2026, expected_action: refuse, yêu cầu tư vấn mang tính chủ quan)

#### 2.5. Điểm chuẩn tuyển sinh (`cutoff_score`) - Hỗ trợ năm 2022 - 2026
- **Câu hỏi hợp lệ (Trong phạm vi, trả lời trực tiếp/fallback)**:
  - "Điểm chuẩn ngành Công nghệ thông tin năm 2025 là bao nhiêu?" (filter_year: 2025, expected_action: answer_specific_year)
  - "Cho em xem điểm trúng tuyển học bạ năm 2024 của ngành Logistics" (filter_year: 2024, expected_action: answer_specific_year)
  - "Điểm chuẩn ngành Kỹ thuật ô tô" (filter_year: null, expected_action: answer_default_2026 / answer_fallback_notice tùy trạng thái dữ liệu năm 2026)
- **Câu hỏi không hợp lệ (Ngoài phạm vi, từ chối)**:
  - "Điểm chuẩn UTH năm 2021 thế nào?" (filter_year: 2021, expected_action: refuse, năm quá khứ xa < 2022)
  - "Dự đoán điểm chuẩn ngành Khoa học dữ liệu năm 2027" (filter_year: 2027, expected_action: refuse, năm tương lai > 2026)

---

### Nhóm II: Thông tin học tập

#### 2.6. Học phí (`tuition_fee`) - Hỗ trợ năm 2026
- **Câu hỏi hợp lệ (Trong phạm vi, trả lời trực tiếp)**:
  - "Học phí năm học 2026 của ngành Điện tử viễn thông là bao nhiêu?" (filter_year: 2026, expected_action: answer_specific_year)
  - "Ngành Logistics học phí bao nhiêu tiền một tín chỉ?" (filter_year: 2026, expected_action: answer_default_2026, tự ngầm định 2026)
- **Câu hỏi không hợp lệ (Ngoài phạm vi, từ chối)**:
  - "Học phí của UTH năm 2023 có đắt không?" (filter_year: 2023, expected_action: refuse, sai năm hỗ trợ)

#### 2.7. Học bổng (`scholarship`) - Hỗ trợ năm 2026
- **Câu hỏi hợp lệ (Trong phạm vi, trả lời trực tiếp)**:
  - "Trường có những loại học bổng nào cho tân sinh viên năm 2026?" (filter_year: 2026, expected_action: answer_specific_year)
  - "Điều kiện nhận học bổng khuyến khích học tập" (filter_year: 2026, expected_action: answer_default_2026, tự ngầm định 2026)
- **Câu hỏi không hợp lệ (Ngoài phạm vi, từ chối)**:
  - "Học bổng năm 2024 yêu cầu điểm GPA bao nhiêu?" (filter_year: 2024, expected_action: refuse, sai năm hỗ trợ)

#### 2.8. Chương trình đào tạo (`curriculum_info`) - Hỗ trợ năm 2026
- **Câu hỏi hợp lệ (Trong phạm vi, trả lời trực tiếp)**:
  - "Chương trình đào tạo ngành Logistics gồm những môn học chuyên ngành nào?" (filter_year: 2026, expected_action: answer_default_2026, tự ngầm định 2026)
  - "Sinh viên ngành CNTT có được đi thực tập doanh nghiệp từ năm mấy?" (filter_year: 2026, expected_action: answer_default_2026, tự ngầm định 2026)
- **Câu hỏi không hợp lệ (Ngoài phạm vi, từ chối)**:
  - "Đề cương chi tiết môn Giải tích 1 có những chương nào?" (filter_year: 2026, expected_action: refuse, ngoài phạm vi thông tin tuyển sinh)

---

### Nhóm III: Thông tin nhập học

#### 2.9. Hồ sơ (`admission_profile`) - Hỗ trợ năm 2026
- **Câu hỏi hợp lệ (Trong phạm vi, trả lời trực tiếp)**:
  - "Hồ sơ nhập học trực tiếp gồm những giấy tờ gì?" (filter_year: 2026, expected_action: answer_default_2026, tự ngầm định 2026)
  - "Giấy chứng nhận tốt nghiệp tạm thời có bắt buộc trong hồ sơ không?" (filter_year: 2026, expected_action: answer_default_2026, tự ngầm định 2026)
- **Câu hỏi không hợp lệ (Ngoài phạm vi, từ chối)**:
  - "Hồ sơ nhập học năm 2024 nộp bản sao hay bản chính?" (filter_year: 2024, expected_action: refuse, sai năm hỗ trợ)

#### 2.10. Thời gian (`admission_time`) - Hỗ trợ năm 2026
- **Câu hỏi hợp lệ (Trong phạm vi, trả lời trực tiếp)**:
  - "Hạn cuối nộp hồ sơ xét học bạ năm 2026 là ngày nào?" (filter_year: 2026, expected_action: answer_specific_year)
  - "Thời gian làm thủ tục nhập học cho tân sinh viên khóa 2026" (filter_year: 2026, expected_action: answer_specific_year)
- **Câu hỏi không hợp lệ (Ngoài phạm vi, từ chối)**:
  - "Khi nào khóa 2024 tập trung quân sự?" (filter_year: 2024, expected_action: refuse, sai năm và ngoài phạm vi tuyển sinh)

#### 2.11. Quy định nhập học (`admission_regulation`) - Hỗ trợ năm 2026
- **Câu hỏi hợp lệ (Trong phạm vi, trả lời trực tiếp)**:
  - "Quy định về việc bảo lưu kết quả trúng tuyển năm 2026 của UTH như thế nào?" (filter_year: 2026, expected_action: answer_specific_year)
  - "Trúng tuyển nhưng nhập học trễ hạn có bị hủy kết quả không?" (filter_year: 2026, expected_action: answer_default_2026, tự ngầm định 2026)
- **Câu hỏi không hợp lệ (Ngoài phạm vi, từ chối)**:
  - "Sinh viên không mặc đồng phục khi đi học có bị kỷ luật không?" (filter_year: 2026, expected_action: refuse, quy chế sinh viên ngoài phạm vi tuyển sinh)

---

### Nhóm IV: Thông tin trường

#### 2.12. Địa chỉ (`address_info`) - Hỗ trợ năm 2026
- **Câu hỏi hợp lệ (Trong phạm vi, trả lời trực tiếp)**:
  - "Địa chỉ cơ sở quận 12 của trường UTH ở đâu?" (filter_year: 2026, expected_action: answer_default_2026, tự ngầm định 2026)
  - "Cơ sở Bình Thạnh của UTH nằm ở đường nào?" (filter_year: 2026, expected_action: answer_default_2026, tự ngầm định 2026)
- **Câu hỏi không hợp lệ (Ngoài phạm vi, từ chối)**:
  - "Hỏi đường đi từ bến xe Miền Đông đến cơ sở Bình Thạnh" (filter_year: 2026, expected_action: refuse, ngoài phạm vi tư vấn tuyển sinh)

#### 2.13. Cơ sở (`campus_info`) - Hỗ trợ năm 2026
- **Câu hỏi hợp lệ (Trong phạm vi, trả lời trực tiếp)**:
  - "Trường có ký túc xá cho sinh viên năm nhất không?" (filter_year: 2026, expected_action: answer_default_2026, tự ngầm định 2026)
  - "Cơ sở vật chất của cơ sở quận 12 gồm những gì?" (filter_year: 2026, expected_action: answer_default_2026, tự ngầm định 2026)
- **Câu hỏi không hợp lệ (Ngoài phạm vi, từ chối)**:
  - "Đăng ký ký túc xá thì phòng nào đẹp và mát nhất?" (filter_year: 2026, expected_action: refuse, ngoài tài liệu chính thức)

#### 2.14. Liên hệ (`contact_info`) - Hỗ trợ năm 2026
- **Câu hỏi hợp lệ (Trong phạm vi, trả lời trực tiếp)**:
  - "Số điện thoại phòng tuyển sinh để em liên hệ hỗ trợ" (filter_year: 2026, expected_action: answer_default_2026, tự ngầm định 2026)
  - "Email liên hệ chính thức của ban tuyển sinh UTH" (filter_year: 2026, expected_action: answer_default_2026, tự ngầm định 2026)
- **Câu hỏi không hợp lệ (Ngoài phạm vi, từ chối)**:
  - "Làm thế nào để kết bạn với admin fanpage tuyển sinh?" (filter_year: 2026, expected_action: refuse, ngoài phạm vi)

---

### Ví dụ Out-of-Scope điển hình khác (Luôn từ chối)
- "Em thi được 23 điểm khối A00 thì có đỗ được ngành CNTT UTH năm nay không?" (Lý do: Yêu cầu định hướng đỗ trượt/Dự đoán)
- "Nên chọn học Logistics ở UTH hay bên UTE tốt hơn?" (Lý do: So sánh liên trường)
- "Ngành nào của trường UTH ra trường có lương cao nhất?" (Lý do: Tư vấn hướng nghiệp)
- "Dự báo điểm chuẩn năm 2026 ngành Kỹ thuật tàu thủy sẽ tăng hay giảm?" (Lý do: Dự báo điểm chuẩn tương lai)
- "Thời tiết hôm nay ở TP.HCM thế nào?" (Lý do: Tán gẫu ngoài lề)

---

## 3. Định dạng Đề xuất cho tệp `test_questions.jsonl`

Khi có tài liệu chính thức, nhóm phát triển sẽ tổ chức tệp câu hỏi kiểm thử dưới định dạng JSON Lines trọng tâm như sau:

```json
{
  "id": "TC_001",
  "question": "Điểm chuẩn ngành Công nghệ thông tin năm 2025 là bao nhiêu?",
  "category": "cutoff_score",
  "filter_year": 2025,
  "is_in_scope": true,
  "expected_action": "answer_specific_year",
  "ground_truth_keywords": ["Công nghệ thông tin", "2025", "điểm chuẩn"]
}
```
