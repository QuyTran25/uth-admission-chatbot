# Kết quả Thực nghiệm Retrieval — DEV SET

> [!IMPORTANT]
**Thông tin thực nghiệm:**
- **Tập dữ liệu:** `backend/data/test/dev_questions.csv` (301 câu in-scope/year-control).
- **Quy chuẩn đối soát (Protocol):** `canonical_mapped`.
- **Cấu hình Alpha SSoT:** `settings.DENSE_WEIGHT = 0.6` (Dense 0.6, BM25 0.4).
- **Bootstrap Resampling:** 1,000 lần (Khoảng tin cậy 95% hai phía).
- **Chế độ lọc năm (CD2):** Sử dụng thời gian thực từ `year_filter.analyze(query)` thay cho nhãn Oracle.

## 1. Bảng 5.1 Tái lập: Hiệu năng Retrieval kèm Bootstrap CI 95%

| Chế độ | Phương pháp | MRR (Mean) | MRR 95% CI | Recall@1 | Recall@1 95% CI | Recall@3 | Recall@5 | Recall@5 95% CI | Recall@10 |
|---|---|---:|:---:|---:|:---:|---:|---:|:---:|---:|
| No-Filter | BM25 | 0.3699 | [0.3261, 0.4173] | 0.2658 | [0.2193, 0.3156] | 0.4352 | 0.4983 | [0.4452, 0.5548] | 0.6346 |
| No-Filter | Dense | 0.2747 | [0.2327, 0.3153] | 0.1794 | [0.1362, 0.2226] | 0.3289 | 0.3920 | [0.3389, 0.4453] | 0.5050 |
| No-Filter | Hybrid_RRF | 0.3800 | [0.3366, 0.4273] | 0.2824 | [0.2326, 0.3355] | 0.4319 | 0.5150 | [0.4618, 0.5681] | 0.6246 |
| No-Filter | Hybrid_Weighted | 0.3611 | [0.3172, 0.4075] | 0.2625 | [0.2159, 0.3123] | 0.4153 | 0.5050 | [0.4518, 0.5615] | 0.6113 |
| Filter | BM25 | 0.4010 | [0.3559, 0.4481] | 0.2924 | [0.2392, 0.3423] | 0.4684 | 0.5449 | [0.4917, 0.6013] | 0.6545 |
| Filter | Dense | 0.3216 | [0.2769, 0.3666] | 0.2226 | [0.1728, 0.2691] | 0.3787 | 0.4419 | [0.3887, 0.4950] | 0.5581 |
| Filter | Hybrid_RRF | 0.4204 | [0.3731, 0.4685] | 0.3355 | [0.2857, 0.3887] | 0.4518 | 0.5316 | [0.4750, 0.5880] | 0.6412 |
| Filter | Hybrid_Weighted | 0.4010 | [0.3538, 0.4493] | 0.2990 | [0.2492, 0.3488] | 0.4551 | 0.5449 | [0.4883, 0.6013] | 0.6445 |

## 2. Kiểm định Thống kê So cặp (Paired Significance Testing)

Đánh giá xem chênh lệch giữa **Hybrid Weighted** và các phương pháp khác có ý nghĩa thống kê hay không:

| Chế độ | Cặp so sánh | Δ MRR | p-value (Paired t-test) | p-value (Wilcoxon) | Ý nghĩa (α=0.05) |
|---|---|---:|---:|---:|:---:|
| No-Filter | Hybrid_Weighted vs Hybrid_RRF | -0.0189 | 0.0418 | 0.0597 | Có (p < 0.05) |
| No-Filter | Hybrid_Weighted vs Dense | +0.0864 | 7.4409e-11 | 4.5783e-12 | Có (p < 0.05) |
| No-Filter | Hybrid_Weighted vs BM25 | -0.0088 | 0.6160 | 0.5379 | Không (p >= 0.05) |
| Filter | Hybrid_Weighted vs Hybrid_RRF | -0.0194 | 0.0460 | 0.1117 | Có (p < 0.05) |
| Filter | Hybrid_Weighted vs Dense | +0.0794 | 1.8272e-09 | 1.2171e-10 | Có (p < 0.05) |
| Filter | Hybrid_Weighted vs BM25 | -0.0001 | 0.9961 | 0.9522 | Không (p >= 0.05) |

## 3. Báo cáo Độ chính xác Nhận diện Năm Tuyển sinh (CD2)

> [!NOTE]
> Để loại bỏ hoàn toàn hiện tượng thổi phồng hiệu năng do lọc bằng nhãn Oracle (Feedback CD2), kịch bản đánh giá đã chuyển sang sử dụng trực tiếp kết quả phân tích thời gian thực từ `year_filter.analyze(query)`.
> Chế độ **Filter** phản ánh năng lực thực tế của toàn bộ pipeline khi nhận diện và lọc năm từ câu truy vấn.

- **Tổng số câu đánh giá:** 301
- **Độ chính xác nhận diện năm tổng thể:** 266/301 (**88.37%**)
- **Độ chính xác trên các câu có nhãn năm xác định:** 263/297 (**88.55%**)

| Năm (Ground Truth) | Số lượng câu (Support) | Nhận diện đúng | Độ chính xác |
|:---:|---:|---:|---:|
| 2022 | 11 | 11 | 100.00% |
| 2023 | 14 | 13 | 92.86% |
| 2024 | 14 | 13 | 92.86% |
| 2025 | 41 | 25 | 60.98% |
| 2026 | 215 | 199 | 92.56% |

## 4. Khảo sát Mô hình Embedding (Embedding Comparison Scope)

> [!NOTE]
**Minh bạch hóa phạm vi mô hình embedding:**
- **Mô hình chính thức sử dụng:** `bkai-foundation-models/vietnamese-bi-encoder` (768 chiều).
- **Lý do không so sánh trực tiếp BGE-M3:** Toàn bộ cơ sở dữ liệu vector hiện tại (`faiss.index`) được lập chỉ mục ở không gian 768 chiều. Mô hình BGE-M3 sinh vector 1024 chiều, dẫn đến lỗi xung đột chiều không gian (Dimension Mismatch) khi truy vấn trên index có sẵn. Để so sánh chuẩn mực cần xây dựng một index 1024 chiều song song. Do đó, trong báo cáo này, chúng tôi **ghi nhận rõ ràng là chưa so sánh đa mô hình embedding**, mà tập trung vào tối ưu hóa chiến lược kết hợp (Fusion Strategy) trên cùng một không gian embedding cơ sở.
