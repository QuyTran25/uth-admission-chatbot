# Báo cáo Thử nghiệm và Đánh giá Retrieval (Retrieval Track)

## 1. Tóm tắt kết quả & Khuyến nghị cấu hình

> [!IMPORTANT]
**Khuyến nghị cấu hình tối ưu:**
* **Phương thức đề xuất:** `Hybrid_Weighted_0.4` trong chế độ **No-Filter Mode** kết hợp định tuyến động.
* **Chỉ số đạt được (Overall):** MRR = `0.3918` | Recall@1 = `0.2875` | Recall@5 = `0.5369`.
* **Lý do lựa chọn:**
  1. Phương pháp **Hybrid Weighted Sum** vượt trội hơn hẳn so với BM25-only và Dense-only đơn lẻ.
  2. **Trọng số alpha = 0.4** (Dense 0.4, BM25 0.6) mang lại sự cân bằng tốt nhất giữa khả năng đối sánh từ khóa chính xác và tương đồng ngữ nghĩa.
  3. **Yêu cầu kỹ thuật bắt buộc cho nhiệm vụ "Kiểm soát năm tuyển sinh" (Admission Year Control) tiếp theo:**
     - **Tầng xử lý đầu vào (Query Pre-processing):** Phải tích hợp bộ nhận diện năm học (sử dụng Regex hoặc mô hình NER) để phát hiện năm tuyển sinh được đề cập trong câu hỏi của người dùng (ví dụ: các số '2023', '2024', '2025', hoặc các từ khóa thời gian như 'năm ngoái', '2 năm trước').
     - **Quy tắc định tuyến (Routing Rule):**
       * **Trường hợp 1 (Có năm cụ thể):** Hệ thống bắt buộc phải áp dụng bộ lọc cứng (`admission_year` lọc theo năm tương ứng) trước khi thực hiện truy vấn Retrieval (tương tự như `Filter Mode` trong thực nghiệm). Điều này đảm bảo triệt tiêu nhiễu từ các năm khác và tối ưu MRR lên mức cao nhất.
       * **Trường hợp 2 (Hỏi chung chung / Không chứa năm):** Hệ thống KHÔNG lọc cứng theo năm tuyển sinh hiện tại (2026) từ đầu. Thay vào đó, thực hiện tìm kiếm trên toàn bộ corpus (`No-Filter Mode` với cấu hình `Hybrid_Weighted_0.4`). Tại tầng hậu xử lý kết quả (Post-processing), áp dụng thuật toán tăng điểm (Boost Score) thêm 20% cho các chunk thuộc năm 2026. Quy tắc này đảm bảo ưu tiên thông tin mới nhất nhưng vẫn giữ khả năng truy xuất thông tin cũ khi cần thiết.

### So sánh nhanh các phương thức chính (Chỉ số Overall)

| Chế độ | Phương pháp | MRR | Recall@1 | Recall@3 | Recall@5 | Recall@10 |
| --- | --- | --- | --- | --- | --- | --- |
| No-Filter | BM25 | 0.3654 | 0.2646 | 0.4275 | 0.4936 | 0.6209 |
| No-Filter | Dense | 0.2860 | 0.1908 | 0.3435 | 0.4020 | 0.5064 |
| No-Filter | Hybrid_RRF | 0.3709 | 0.2697 | 0.4275 | 0.5064 | 0.6081 |
| No-Filter | Hybrid_Weighted_0.4 | 0.3918 | 0.2875 | 0.4351 | 0.5369 | 0.6412 |
| Filter | BM25 | 0.3893 | 0.2875 | 0.4478 | 0.5293 | 0.6310 |
| Filter | Dense | 0.3388 | 0.2519 | 0.3919 | 0.4453 | 0.5344 |
| Filter | Hybrid_RRF | 0.4135 | 0.3282 | 0.4453 | 0.5293 | 0.6310 |
| Filter | Hybrid_Weighted_0.4 | 0.4329 | 0.3333 | 0.4758 | 0.5725 | 0.6692 |

### So sánh Recall@1 và Recall@5 theo phân nhóm (Cấu hình Hybrid_Weighted_0.4)

| Chế độ | Phân nhóm | Recall@1 | Recall@5 |
| :--- | :--- | :--- | :--- |
| **No-Filter** | IN_SCOPE | 0.2893 | 0.5620 |
| **No-Filter** | YEAR_CONTROL | 0.3185 | 0.5481 |
| **Filter** | IN_SCOPE | 0.3264 | 0.6240 |
| **Filter** | YEAR_CONTROL | 0.3852 | 0.5333 |

## 2. Phân tích nguyên nhân chỉ số Recall@1 thấp so với Recall@5

> [!NOTE]
**Khoảng cách lớn giữa Recall@1 (~0.29 - 0.33) và Recall@5 (~0.53 - 0.57):**
Chunk đúng thường nằm ở top 2-5 chứ không phải top 1. Nguyên nhân chính bao gồm:
1. **Sự trùng lặp cấu trúc thông tin xuyên suốt các năm:** Các tài liệu tuyển sinh (quy định tuyển thẳng, chính sách học phí, điều kiện học bổng, điểm chuẩn) giữa các năm 2023, 2024, 2025, và 2026 có nội dung cực kỳ tương đồng về mặt từ ngữ. Khi chạy chế độ No-Filter, các chunk của nhiều năm khác nhau đều có điểm tương đồng ngữ nghĩa và từ khóa rất cao, gây hiện tượng tranh chấp vị trí top 1 (ví dụ: chunk 2025 đứng top 1 còn chunk đích 2026 bị đẩy xuống top 2-3).
2. **Chất lượng dữ liệu và OCR:** Một số tài liệu scan có nhiễu OCR (ví dụ: 'Chưong trinh dào ta0'), làm giảm khả năng đối sánh từ khóa chính xác của BM25 và độ khớp ngữ nghĩa của Dense.

**Phân rã (Breakdown) Recall@1 và MRR của Hybrid_Weighted_0.4 theo phân nhóm:**

| Chế độ | Phân nhóm | MRR | Recall@1 | Recall@3 | Recall@5 | Recall@10 |
| --- | --- | --- | --- | --- | --- | --- |
| No-Filter | OVERALL | 0.3918 | 0.2875 | 0.4351 | 0.5369 | 0.6412 |
| No-Filter | IN_SCOPE | 0.4006 | 0.2893 | 0.4339 | 0.5620 | 0.6860 |
| No-Filter | YEAR_CONTROL | 0.4207 | 0.3185 | 0.4889 | 0.5481 | 0.6296 |
| Filter | OVERALL | 0.4329 | 0.3333 | 0.4758 | 0.5725 | 0.6692 |
| Filter | IN_SCOPE | 0.4490 | 0.3264 | 0.4959 | 0.6240 | 0.7479 |
| Filter | YEAR_CONTROL | 0.4511 | 0.3852 | 0.4889 | 0.5333 | 0.5926 |

> [!TIP]
**Nhận xét quan trọng:**
* Nhóm **`year_control` đạt Recall@1 tốt hơn đáng kể so với `in_scope`** ở cả 2 chế độ (No-Filter: 31.85% vs 28.93%; Filter: 38.52% vs 32.64%).
* Điều này là do các câu hỏi thuộc nhóm `year_control` chứa từ khóa năm rõ ràng (ví dụ: 'năm 2023'), giúp mô hình dễ định vị đúng chunk đích thông qua bộ lọc năm hoặc thông qua khớp token năm. 
* Với nhóm `in_scope` (hỏi chung chung, không chỉ rõ năm, ngầm định hỏi năm nay), việc thiếu từ khóa năm cụ thể trong câu hỏi khiến retriever dễ bị nhầm lẫn giữa các chunk cùng chủ đề của các năm khác nhau. Điều này chứng minh rằng việc xây dựng bộ nhận diện năm ở tầng truy vấn (định hướng sang Filter Mode thích hợp) là vô cùng cần thiết để giải quyết tận gốc hiện tượng nhầm lẫn năm học.

## 3. Ghi chú về việc thay đổi mô hình Embedding

> [!NOTE]
Trong quá trình thực nghiệm, hệ thống đã được chuyển đổi mô hình embedding từ **BGE-M3 (1024 chiều)** sang **bkai-foundation-models/vietnamese-bi-encoder (768 chiều)**:
* **Nguyên nhân chuyển đổi:** Phát hiện lỗi không đồng nhất kích thước vector (Dimension Mismatch). File index FAISS cũ được tạo bằng BGE-M3 (1024 chiều), nhưng cấu hình hệ thống hiện tại mặc định sử dụng bkai (768 chiều) để encode query, dẫn đến lỗi crash FAISS khi thực hiện truy vấn Dense.
* **Lưu ý quan trọng về benchmark:** Hiện tại các thử nghiệm mới chỉ được thực hiện trên mô hình embedding mặc định của hệ thống (`bkai-foundation-models/vietnamese-bi-encoder`). Chúng ta **chưa benchmark** các mô hình embedding khác (như BGE-M3, PhoBERT, Cohere, OpenAI...).
* **Giải pháp đã thực hiện:** Để đảm bảo tính nhất quán và ổn định của mã nguồn repo gốc, chúng tôi đã tiến hành rebuild đồng bộ toàn bộ chỉ mục FAISS và BM25 theo mô hình bkai mặc định kết hợp tách từ tiếng Việt (Word Segmentation).
* **Hướng phát triển tiếp theo:** Việc khảo sát hiệu năng giữa các mô hình embedding khác nhau sẽ được đưa vào kế hoạch nghiên cứu ở giai đoạn sau khi đã tối ưu cấu hình cơ sở.

## 4. Báo cáo phân tích dữ liệu bất thường (Data Anomalies)

> [!WARNING]
**Missing Chunks trong Index:**
* Phát hiện **4 chunk IDs** làm đích của **9 câu hỏi** trong bộ test chưa được lập chỉ mục (index) trong FAISS và BM25.
* Các chunk bị thiếu bao gồm:
  - `2023_diem-chuan_dai-hoc-chinh-quy_t000_r000`
  - `2024_diem-chuan_dai-hoc-chinh-quy_t000_r000`
  - `2025_diem-chuan_dai-hoc-chinh-quy_t000_r000`
  - `thong_tin_chung_2026_co-so_chunks`
* **Ảnh hưởng:** 9 câu hỏi này mặc định bị coi là thất bại ở mọi phương pháp (rank = inf, score = 0). Điều này làm Recall@1 của tất cả các thuật toán bị "trừ điểm oan" khoảng **2.29%**.
* **Lưu ý cho việc hiệu chỉnh Retrieval Gate (Người B):** 9 câu hỏi này đạt điểm score = 0 ở mọi phương pháp **là do lỗi thiếu dữ liệu index, không phải do model từ chối đúng (Out-of-Scope)**. Khi tính toán ngưỡng cho Retrieval Gate, Người B cần loại bỏ hoặc hiệu chỉnh 9 câu này để tránh làm lệch ngưỡng tối ưu.
* **Hành động khắc phục & Deadline:** Chúng tôi đã báo cáo chi tiết danh sách 4 chunk thiếu này cho bộ phận kỹ thuật phụ trách dữ liệu. Phía dữ liệu đã xác nhận nhận thông tin và cam kết bổ sung đầy đủ 4 chunk này vào bản build tiếp theo. **Deadline dự kiến hoàn thành cập nhật index là ngày 28/08/2026 (Thứ Sáu tuần này).**

## 5. Khảo sát tham số alpha trong Hybrid Weighted

Bảng dưới đây thể hiện tác động của trọng số `alpha` (Dense Weight) đối với phương pháp Hybrid Weighted Sum trong chế độ **No-Filter Mode**:

| Alpha (Dense Weight) | MRR | Recall@1 | Recall@3 | Recall@5 | Recall@10 |
| --- | --- | --- | --- | --- | --- |
| 0.1 | 0.3733 | 0.2723 | 0.4300 | 0.5115 | 0.6158 |
| 0.2 | 0.3790 | 0.2748 | 0.4351 | 0.5191 | 0.6234 |
| 0.3 | 0.3849 | 0.2799 | 0.4326 | 0.5369 | 0.6387 |
| 0.4 | 0.3918 | 0.2875 | 0.4351 | 0.5369 | 0.6412 |
| 0.5 | 0.3782 | 0.2748 | 0.4326 | 0.5242 | 0.6285 |
| 0.6 | 0.3633 | 0.2646 | 0.4173 | 0.4962 | 0.6056 |
| 0.7 | 0.3478 | 0.2519 | 0.4020 | 0.4758 | 0.5827 |
| 0.8 | 0.3203 | 0.2214 | 0.3893 | 0.4555 | 0.5471 |
| 0.9 | 0.3046 | 0.2112 | 0.3664 | 0.4300 | 0.5191 |

## 6. Chi tiết bảng so sánh Precision và Recall (k = 1, 3, 5, 10)

### Chế độ: No-Filter Mode

#### Phân nhóm: OVERALL

| Phương pháp | MRR | Recall@1 | Precision@1 | Recall@3 | Precision@3 | Recall@5 | Precision@5 | Recall@10 | Precision@10 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Hybrid_Weighted_0.4 | 0.3918 | 0.2875 | 0.2875 | 0.4351 | 0.1450 | 0.5369 | 0.1074 | 0.6412 | 0.0641 |
| Hybrid_Weighted_0.3 | 0.3849 | 0.2799 | 0.2799 | 0.4326 | 0.1442 | 0.5369 | 0.1074 | 0.6387 | 0.0639 |
| Hybrid_Weighted_0.2 | 0.3790 | 0.2748 | 0.2748 | 0.4351 | 0.1450 | 0.5191 | 0.1038 | 0.6234 | 0.0623 |
| Hybrid_Weighted_0.5 | 0.3782 | 0.2748 | 0.2748 | 0.4326 | 0.1442 | 0.5242 | 0.1048 | 0.6285 | 0.0628 |
| Hybrid_Weighted_0.1 | 0.3733 | 0.2723 | 0.2723 | 0.4300 | 0.1433 | 0.5115 | 0.1023 | 0.6158 | 0.0616 |
| Hybrid_RRF | 0.3709 | 0.2697 | 0.2697 | 0.4275 | 0.1425 | 0.5064 | 0.1013 | 0.6081 | 0.0608 |
| BM25 | 0.3654 | 0.2646 | 0.2646 | 0.4275 | 0.1425 | 0.4936 | 0.0987 | 0.6209 | 0.0621 |
| Hybrid_Weighted_0.6 | 0.3633 | 0.2646 | 0.2646 | 0.4173 | 0.1391 | 0.4962 | 0.0992 | 0.6056 | 0.0606 |
| Hybrid_Weighted_0.7 | 0.3478 | 0.2519 | 0.2519 | 0.4020 | 0.1340 | 0.4758 | 0.0952 | 0.5827 | 0.0583 |
| Hybrid_Weighted_0.8 | 0.3203 | 0.2214 | 0.2214 | 0.3893 | 0.1298 | 0.4555 | 0.0911 | 0.5471 | 0.0547 |
| Hybrid_Weighted_0.9 | 0.3046 | 0.2112 | 0.2112 | 0.3664 | 0.1221 | 0.4300 | 0.0860 | 0.5191 | 0.0519 |
| Dense | 0.2860 | 0.1908 | 0.1908 | 0.3435 | 0.1145 | 0.4020 | 0.0804 | 0.5064 | 0.0506 |

#### Phân nhóm: IN_SCOPE

| Phương pháp | MRR | Recall@1 | Precision@1 | Recall@3 | Precision@3 | Recall@5 | Precision@5 | Recall@10 | Precision@10 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Hybrid_Weighted_0.4 | 0.4006 | 0.2893 | 0.2893 | 0.4339 | 0.1446 | 0.5620 | 0.1124 | 0.6860 | 0.0686 |
| Hybrid_Weighted_0.3 | 0.4004 | 0.2893 | 0.2893 | 0.4380 | 0.1460 | 0.5785 | 0.1157 | 0.6860 | 0.0686 |
| Hybrid_Weighted_0.2 | 0.3960 | 0.2851 | 0.2851 | 0.4421 | 0.1474 | 0.5537 | 0.1107 | 0.6694 | 0.0669 |
| Hybrid_Weighted_0.1 | 0.3903 | 0.2810 | 0.2810 | 0.4421 | 0.1474 | 0.5455 | 0.1091 | 0.6653 | 0.0665 |
| Hybrid_Weighted_0.5 | 0.3900 | 0.2851 | 0.2851 | 0.4298 | 0.1433 | 0.5496 | 0.1099 | 0.6694 | 0.0669 |
| BM25 | 0.3829 | 0.2727 | 0.2727 | 0.4421 | 0.1474 | 0.5331 | 0.1066 | 0.6777 | 0.0678 |
| Hybrid_RRF | 0.3809 | 0.2810 | 0.2810 | 0.4215 | 0.1405 | 0.5165 | 0.1033 | 0.6446 | 0.0645 |
| Hybrid_Weighted_0.6 | 0.3759 | 0.2769 | 0.2769 | 0.4091 | 0.1364 | 0.5165 | 0.1033 | 0.6529 | 0.0653 |
| Hybrid_Weighted_0.7 | 0.3515 | 0.2479 | 0.2479 | 0.4008 | 0.1336 | 0.4959 | 0.0992 | 0.6281 | 0.0628 |
| Hybrid_Weighted_0.8 | 0.3219 | 0.2149 | 0.2149 | 0.3884 | 0.1295 | 0.4669 | 0.0934 | 0.5785 | 0.0579 |
| Hybrid_Weighted_0.9 | 0.3034 | 0.1983 | 0.1983 | 0.3719 | 0.1240 | 0.4421 | 0.0884 | 0.5537 | 0.0554 |
| Dense | 0.2934 | 0.1901 | 0.1901 | 0.3554 | 0.1185 | 0.4215 | 0.0843 | 0.5496 | 0.0550 |

#### Phân nhóm: YEAR_CONTROL

| Phương pháp | MRR | Recall@1 | Precision@1 | Recall@3 | Precision@3 | Recall@5 | Precision@5 | Recall@10 | Precision@10 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Hybrid_Weighted_0.4 | 0.4207 | 0.3185 | 0.3185 | 0.4889 | 0.1630 | 0.5481 | 0.1096 | 0.6296 | 0.0630 |
| Hybrid_Weighted_0.3 | 0.4017 | 0.2963 | 0.2963 | 0.4741 | 0.1580 | 0.5259 | 0.1052 | 0.6222 | 0.0622 |
| Hybrid_Weighted_0.5 | 0.3946 | 0.2815 | 0.2815 | 0.4815 | 0.1605 | 0.5333 | 0.1067 | 0.6222 | 0.0622 |
| Hybrid_Weighted_0.2 | 0.3935 | 0.2889 | 0.2889 | 0.4741 | 0.1580 | 0.5185 | 0.1037 | 0.6148 | 0.0615 |
| Hybrid_RRF | 0.3931 | 0.2815 | 0.2815 | 0.4815 | 0.1605 | 0.5407 | 0.1081 | 0.6074 | 0.0607 |
| Hybrid_Weighted_0.1 | 0.3871 | 0.2889 | 0.2889 | 0.4593 | 0.1531 | 0.5111 | 0.1022 | 0.6000 | 0.0600 |
| BM25 | 0.3775 | 0.2815 | 0.2815 | 0.4519 | 0.1506 | 0.4815 | 0.0963 | 0.5926 | 0.0593 |
| Hybrid_Weighted_0.6 | 0.3764 | 0.2667 | 0.2667 | 0.4741 | 0.1580 | 0.5111 | 0.1022 | 0.5852 | 0.0585 |
| Hybrid_Weighted_0.7 | 0.3749 | 0.2815 | 0.2815 | 0.4444 | 0.1481 | 0.4889 | 0.0978 | 0.5630 | 0.0563 |
| Hybrid_Weighted_0.8 | 0.3479 | 0.2519 | 0.2519 | 0.4296 | 0.1432 | 0.4815 | 0.0963 | 0.5481 | 0.0548 |
| Hybrid_Weighted_0.9 | 0.3355 | 0.2519 | 0.2519 | 0.3926 | 0.1309 | 0.4519 | 0.0904 | 0.5111 | 0.0511 |
| Dense | 0.2993 | 0.2074 | 0.2074 | 0.3556 | 0.1185 | 0.4074 | 0.0815 | 0.4815 | 0.0481 |

### Chế độ: Filter Mode

#### Phân nhóm: OVERALL

| Phương pháp | MRR | Recall@1 | Precision@1 | Recall@3 | Precision@3 | Recall@5 | Precision@5 | Recall@10 | Precision@10 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Hybrid_Weighted_0.4 | 0.4329 | 0.3333 | 0.3333 | 0.4758 | 0.1586 | 0.5725 | 0.1145 | 0.6692 | 0.0669 |
| Hybrid_Weighted_0.5 | 0.4282 | 0.3282 | 0.3282 | 0.4809 | 0.1603 | 0.5725 | 0.1145 | 0.6616 | 0.0662 |
| Hybrid_Weighted_0.3 | 0.4212 | 0.3155 | 0.3155 | 0.4682 | 0.1561 | 0.5725 | 0.1145 | 0.6641 | 0.0664 |
| Hybrid_RRF | 0.4135 | 0.3282 | 0.3282 | 0.4453 | 0.1484 | 0.5293 | 0.1059 | 0.6310 | 0.0631 |
| Hybrid_Weighted_0.6 | 0.4131 | 0.3155 | 0.3155 | 0.4606 | 0.1535 | 0.5522 | 0.1104 | 0.6412 | 0.0641 |
| Hybrid_Weighted_0.2 | 0.4116 | 0.3053 | 0.3053 | 0.4707 | 0.1569 | 0.5573 | 0.1115 | 0.6616 | 0.0662 |
| Hybrid_Weighted_0.1 | 0.4040 | 0.3003 | 0.3003 | 0.4631 | 0.1544 | 0.5522 | 0.1104 | 0.6514 | 0.0651 |
| Hybrid_Weighted_0.7 | 0.3984 | 0.3028 | 0.3028 | 0.4478 | 0.1493 | 0.5267 | 0.1053 | 0.6234 | 0.0623 |
| BM25 | 0.3893 | 0.2875 | 0.2875 | 0.4478 | 0.1493 | 0.5293 | 0.1059 | 0.6310 | 0.0631 |
| Hybrid_Weighted_0.8 | 0.3777 | 0.2774 | 0.2774 | 0.4427 | 0.1476 | 0.5038 | 0.1008 | 0.5903 | 0.0590 |
| Hybrid_Weighted_0.9 | 0.3661 | 0.2723 | 0.2723 | 0.4275 | 0.1425 | 0.4911 | 0.0982 | 0.5751 | 0.0575 |
| Dense | 0.3388 | 0.2519 | 0.2519 | 0.3919 | 0.1306 | 0.4453 | 0.0891 | 0.5344 | 0.0534 |

#### Phân nhóm: IN_SCOPE

| Phương pháp | MRR | Recall@1 | Precision@1 | Recall@3 | Precision@3 | Recall@5 | Precision@5 | Recall@10 | Precision@10 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Hybrid_Weighted_0.4 | 0.4490 | 0.3264 | 0.3264 | 0.4959 | 0.1653 | 0.6240 | 0.1248 | 0.7479 | 0.0748 |
| Hybrid_Weighted_0.3 | 0.4426 | 0.3140 | 0.3140 | 0.4959 | 0.1653 | 0.6364 | 0.1273 | 0.7438 | 0.0744 |
| Hybrid_Weighted_0.2 | 0.4404 | 0.3140 | 0.3140 | 0.5083 | 0.1694 | 0.6116 | 0.1223 | 0.7438 | 0.0744 |
| Hybrid_Weighted_0.5 | 0.4386 | 0.3182 | 0.3182 | 0.5000 | 0.1667 | 0.6157 | 0.1231 | 0.7355 | 0.0736 |
| Hybrid_Weighted_0.1 | 0.4326 | 0.3099 | 0.3099 | 0.5000 | 0.1667 | 0.6074 | 0.1215 | 0.7355 | 0.0736 |
| Hybrid_RRF | 0.4271 | 0.3306 | 0.3306 | 0.4545 | 0.1515 | 0.5579 | 0.1116 | 0.6860 | 0.0686 |
| Hybrid_Weighted_0.6 | 0.4249 | 0.3099 | 0.3099 | 0.4669 | 0.1556 | 0.5950 | 0.1190 | 0.7107 | 0.0711 |
| BM25 | 0.4147 | 0.2934 | 0.2934 | 0.4793 | 0.1598 | 0.5826 | 0.1165 | 0.7107 | 0.0711 |
| Hybrid_Weighted_0.7 | 0.4042 | 0.2893 | 0.2893 | 0.4628 | 0.1543 | 0.5661 | 0.1132 | 0.6777 | 0.0678 |
| Hybrid_Weighted_0.8 | 0.3763 | 0.2562 | 0.2562 | 0.4545 | 0.1515 | 0.5289 | 0.1058 | 0.6281 | 0.0628 |
| Hybrid_Weighted_0.9 | 0.3600 | 0.2438 | 0.2438 | 0.4421 | 0.1474 | 0.5083 | 0.1017 | 0.6116 | 0.0612 |
| Dense | 0.3433 | 0.2355 | 0.2355 | 0.4132 | 0.1377 | 0.4711 | 0.0942 | 0.5909 | 0.0591 |

#### Phân nhóm: YEAR_CONTROL

| Phương pháp | MRR | Recall@1 | Precision@1 | Recall@3 | Precision@3 | Recall@5 | Precision@5 | Recall@10 | Precision@10 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Hybrid_Weighted_0.5 | 0.4512 | 0.3778 | 0.3778 | 0.4963 | 0.1654 | 0.5481 | 0.1096 | 0.5926 | 0.0593 |
| Hybrid_Weighted_0.4 | 0.4511 | 0.3852 | 0.3852 | 0.4889 | 0.1630 | 0.5333 | 0.1067 | 0.5926 | 0.0593 |
| Hybrid_RRF | 0.4337 | 0.3630 | 0.3630 | 0.4741 | 0.1580 | 0.5333 | 0.1067 | 0.5926 | 0.0593 |
| Hybrid_Weighted_0.6 | 0.4311 | 0.3556 | 0.3556 | 0.4889 | 0.1630 | 0.5259 | 0.1052 | 0.5778 | 0.0578 |
| Hybrid_Weighted_0.3 | 0.4308 | 0.3556 | 0.3556 | 0.4741 | 0.1580 | 0.5259 | 0.1052 | 0.5852 | 0.0585 |
| Hybrid_Weighted_0.7 | 0.4253 | 0.3556 | 0.3556 | 0.4593 | 0.1531 | 0.5037 | 0.1007 | 0.5852 | 0.0585 |
| Hybrid_Weighted_0.8 | 0.4150 | 0.3407 | 0.3407 | 0.4593 | 0.1531 | 0.5037 | 0.1007 | 0.5778 | 0.0578 |
| Hybrid_Weighted_0.9 | 0.4104 | 0.3481 | 0.3481 | 0.4370 | 0.1457 | 0.5037 | 0.1007 | 0.5630 | 0.0563 |
| Hybrid_Weighted_0.2 | 0.4080 | 0.3259 | 0.3259 | 0.4593 | 0.1531 | 0.5259 | 0.1052 | 0.5852 | 0.0585 |
| Hybrid_Weighted_0.1 | 0.4005 | 0.3185 | 0.3185 | 0.4519 | 0.1506 | 0.5185 | 0.1037 | 0.5778 | 0.0578 |
| BM25 | 0.3899 | 0.3111 | 0.3111 | 0.4444 | 0.1481 | 0.4963 | 0.0993 | 0.5630 | 0.0563 |
| Dense | 0.3609 | 0.3037 | 0.3037 | 0.3852 | 0.1284 | 0.4370 | 0.0874 | 0.4815 | 0.0481 |

