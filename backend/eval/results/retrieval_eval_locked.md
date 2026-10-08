# Kết quả Thực nghiệm Retrieval — LOCKED SET

> [!IMPORTANT]
**Thông tin thực nghiệm:**
- **Tập dữ liệu:** `backend/data/test/test_questions_locked.csv` (78 câu in-scope/year-control).
- **Quy chuẩn đối soát (Protocol):** `canonical_mapped`.
- **Cấu hình Alpha SSoT:** `settings.DENSE_WEIGHT = 0.6` (Dense 0.6, BM25 0.4).
- **Bootstrap Resampling:** 1,000 lần (Khoảng tin cậy 95% hai phía).
- **Chế độ lọc năm (CD2):** Sử dụng thời gian thực từ `year_filter.analyze(query)` thay cho nhãn Oracle.

## 1. Bảng 5.1 Tái lập: Hiệu năng Retrieval kèm Bootstrap CI 95%

| Chế độ | Phương pháp | MRR (Mean) | MRR 95% CI | Recall@1 | Recall@1 95% CI | Recall@3 | Recall@5 | Recall@5 95% CI | Recall@10 |
|---|---|---:|:---:|---:|:---:|---:|---:|:---:|---:|
| No-Filter | BM25 | 0.2986 | [0.2082, 0.3866] | 0.2308 | [0.1410, 0.3205] | 0.2821 | 0.4103 | [0.2949, 0.5128] | 0.5256 |
| No-Filter | Dense | 0.2702 | [0.1908, 0.3475] | 0.1410 | [0.0641, 0.2179] | 0.3846 | 0.4487 | [0.3333, 0.5513] | 0.5128 |
| No-Filter | Hybrid_RRF | 0.3545 | [0.2629, 0.4403] | 0.2436 | [0.1410, 0.3333] | 0.3974 | 0.4872 | [0.3718, 0.5897] | 0.6410 |
| No-Filter | Hybrid_Weighted | 0.3334 | [0.2444, 0.4133] | 0.2051 | [0.1154, 0.2949] | 0.4487 | 0.5385 | [0.4103, 0.6413] | 0.5769 |
| Filter | BM25 | 0.3287 | [0.2372, 0.4203] | 0.2436 | [0.1410, 0.3462] | 0.3590 | 0.5000 | [0.3846, 0.6154] | 0.5513 |
| Filter | Dense | 0.3396 | [0.2500, 0.4258] | 0.2179 | [0.1282, 0.3077] | 0.4231 | 0.5385 | [0.4231, 0.6410] | 0.6026 |
| Filter | Hybrid_RRF | 0.3747 | [0.2808, 0.4640] | 0.2564 | [0.1538, 0.3590] | 0.4359 | 0.5513 | [0.4231, 0.6667] | 0.6282 |
| Filter | Hybrid_Weighted | 0.3878 | [0.2916, 0.4733] | 0.2436 | [0.1410, 0.3337] | 0.5000 | 0.5897 | [0.4744, 0.6923] | 0.6667 |

## 2. Kiểm định Thống kê So cặp (Paired Significance Testing)

Đánh giá xem chênh lệch giữa **Hybrid Weighted** và các phương pháp khác có ý nghĩa thống kê hay không:

| Chế độ | Cặp so sánh | Δ MRR | p-value (Paired t-test) | p-value (Wilcoxon) | Ý nghĩa (α=0.05) |
|---|---|---:|---:|---:|:---:|
| No-Filter | Hybrid_Weighted vs Hybrid_RRF | -0.0211 | 0.3166 | 0.4182 | Không (p >= 0.05) |
| No-Filter | Hybrid_Weighted vs Dense | +0.0631 | 0.0082 | 0.0062 | Có (p < 0.05) |
| No-Filter | Hybrid_Weighted vs BM25 | +0.0348 | 0.3101 | 0.2238 | Không (p >= 0.05) |
| Filter | Hybrid_Weighted vs Hybrid_RRF | +0.0131 | 0.5896 | 0.5933 | Không (p >= 0.05) |
| Filter | Hybrid_Weighted vs Dense | +0.0482 | 0.0449 | 0.0178 | Có (p < 0.05) |
| Filter | Hybrid_Weighted vs BM25 | +0.0591 | 0.1151 | 0.1135 | Không (p >= 0.05) |

## 3. Báo cáo Độ chính xác Nhận diện Năm Tuyển sinh (CD2)

> [!NOTE]
> Để loại bỏ hoàn toàn hiện tượng thổi phồng hiệu năng do lọc bằng nhãn Oracle (Feedback CD2), kịch bản đánh giá đã chuyển sang sử dụng trực tiếp kết quả phân tích thời gian thực từ `year_filter.analyze(query)`.
> Chế độ **Filter** phản ánh năng lực thực tế của toàn bộ pipeline khi nhận diện và lọc năm từ câu truy vấn.

- **Tổng số câu đánh giá:** 78
- **Độ chính xác nhận diện năm tổng thể:** 71/78 (**91.03%**)
- **Độ chính xác trên các câu có nhãn năm xác định:** 71/78 (**91.03%**)

| Năm (Ground Truth) | Số lượng câu (Support) | Nhận diện đúng | Độ chính xác |
|:---:|---:|---:|---:|
| 2022 | 2 | 2 | 100.00% |
| 2023 | 5 | 5 | 100.00% |
| 2024 | 5 | 5 | 100.00% |
| 2025 | 8 | 8 | 100.00% |
| 2026 | 57 | 50 | 87.72% |

## 4. Khảo sát Mô hình Embedding (Embedding Comparison Scope)

> [!NOTE]
**Minh bạch hóa phạm vi mô hình embedding:**
- **Mô hình chính thức sử dụng:** `bkai-foundation-models/vietnamese-bi-encoder` (768 chiều).
- **Lý do không so sánh trực tiếp BGE-M3:** Toàn bộ cơ sở dữ liệu vector hiện tại (`faiss.index`) được lập chỉ mục ở không gian 768 chiều. Mô hình BGE-M3 sinh vector 1024 chiều, dẫn đến lỗi xung đột chiều không gian (Dimension Mismatch) khi truy vấn trên index có sẵn. Để so sánh chuẩn mực cần xây dựng một index 1024 chiều song song. Do đó, trong báo cáo này, chúng tôi **ghi nhận rõ ràng là chưa so sánh đa mô hình embedding**, mà tập trung vào tối ưu hóa chiến lược kết hợp (Fusion Strategy) trên cùng một không gian embedding cơ sở.
