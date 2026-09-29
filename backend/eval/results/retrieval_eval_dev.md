# Kết quả Thực nghiệm Retrieval — DEV SET

> [!IMPORTANT]
**Thông tin thực nghiệm:**
- **Tập dữ liệu:** `backend/data/test/dev_questions.csv` (301 câu in-scope/year-control).
- **Quy chuẩn đối soát (Protocol):** `canonical_mapped`.
- **Cấu hình Alpha SSoT:** `settings.DENSE_WEIGHT = 0.6` (Dense 0.6, BM25 0.4).
- **Bootstrap Resampling:** 1,000 lần (Khoảng tin cậy 95% hai phía).

## 1. Bảng 5.1 Tái lập: Hiệu năng Retrieval kèm Bootstrap CI 95%

| Chế độ | Phương pháp | MRR (Mean) | MRR 95% CI | Recall@1 | Recall@1 95% CI | Recall@3 | Recall@5 | Recall@5 95% CI | Recall@10 |
|---|---|---:|:---:|---:|:---:|---:|---:|:---:|---:|
| No-Filter | BM25 | 0.3699 | [0.3261, 0.4173] | 0.2658 | [0.2193, 0.3156] | 0.4352 | 0.4983 | [0.4452, 0.5548] | 0.6346 |
| No-Filter | Dense | 0.2747 | [0.2327, 0.3153] | 0.1794 | [0.1362, 0.2226] | 0.3289 | 0.3920 | [0.3389, 0.4453] | 0.5050 |
| No-Filter | Hybrid_RRF | 0.3800 | [0.3366, 0.4273] | 0.2824 | [0.2326, 0.3355] | 0.4319 | 0.5150 | [0.4618, 0.5681] | 0.6246 |
| No-Filter | Hybrid_Weighted | 0.3611 | [0.3172, 0.4075] | 0.2625 | [0.2159, 0.3123] | 0.4153 | 0.5050 | [0.4518, 0.5615] | 0.6113 |
| Filter | BM25 | 0.4008 | [0.3550, 0.4504] | 0.2957 | [0.2425, 0.3488] | 0.4618 | 0.5449 | [0.4884, 0.6013] | 0.6545 |
| Filter | Dense | 0.3258 | [0.2806, 0.3718] | 0.2359 | [0.1860, 0.2857] | 0.3821 | 0.4385 | [0.3821, 0.4917] | 0.5349 |
| Filter | Hybrid_RRF | 0.4260 | [0.3787, 0.4753] | 0.3422 | [0.2890, 0.3953] | 0.4551 | 0.5349 | [0.4784, 0.5914] | 0.6478 |
| Filter | Hybrid_Weighted | 0.4140 | [0.3688, 0.4644] | 0.3156 | [0.2625, 0.3688] | 0.4618 | 0.5581 | [0.5017, 0.6146] | 0.6545 |

## 2. Kiểm định Thống kê So cặp (Paired Significance Testing)

Đánh giá xem chênh lệch giữa **Hybrid Weighted** và các phương pháp khác có ý nghĩa thống kê hay không:

| Chế độ | Cặp so sánh | Δ MRR | p-value (Paired t-test) | p-value (Wilcoxon) | Ý nghĩa (α=0.05) |
|---|---|---:|---:|---:|:---:|
| No-Filter | Hybrid_Weighted vs Hybrid_RRF | -0.0189 | 0.0418 | 0.0597 | Có (p < 0.05) |
| No-Filter | Hybrid_Weighted vs Dense | +0.0864 | 7.4409e-11 | 4.5783e-12 | Có (p < 0.05) |
| No-Filter | Hybrid_Weighted vs BM25 | -0.0088 | 0.6160 | 0.5379 | Không (p >= 0.05) |
| Filter | Hybrid_Weighted vs Hybrid_RRF | -0.0120 | 0.2483 | 0.2682 | Không (p >= 0.05) |
| Filter | Hybrid_Weighted vs Dense | +0.0882 | 7.0579e-10 | 5.1527e-11 | Có (p < 0.05) |
| Filter | Hybrid_Weighted vs BM25 | +0.0132 | 0.4647 | 0.4878 | Không (p >= 0.05) |

## 3. Khảo sát Mô hình Embedding (Embedding Comparison Scope)

> [!NOTE]
**Minh bạch hóa phạm vi mô hình embedding:**
- **Mô hình chính thức sử dụng:** `bkai-foundation-models/vietnamese-bi-encoder` (768 chiều).
- **Lý do không so sánh trực tiếp BGE-M3:** Toàn bộ cơ sở dữ liệu vector hiện tại (`faiss.index`) được lập chỉ mục ở không gian 768 chiều. Mô hình BGE-M3 sinh vector 1024 chiều, dẫn đến lỗi xung đột chiều không gian (Dimension Mismatch) khi truy vấn trên index có sẵn. Để so sánh chuẩn mực cần xây dựng một index 1024 chiều song song. Do đó, trong báo cáo này, chúng tôi **ghi nhận rõ ràng là chưa so sánh đa mô hình embedding**, mà tập trung vào tối ưu hóa chiến lược kết hợp (Fusion Strategy) trên cùng một không gian embedding cơ sở.
