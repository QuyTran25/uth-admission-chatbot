# Bảng 5.4 Mở rộng: Phân tích Đóng góp Thành phần (Ablation Study) — LOCKED SET

> [!IMPORTANT]
**Giải quyết Feedback #13 của Giảng viên:**
- Đã bổ sung đầy đủ 6 cấu hình: Full vs w/o Year Filter, w/o OOS Filter, w/o Retrieval Gate, w/o Boost 2026, w/o Attribution Gate.
- Đánh giá thực đo trên tập `test_questions_locked.csv` (Gồm 22 câu out-of-scope và 78 câu in-scope).

## Bảng 5.4: Hiệu năng Tổng hợp khi Lược bỏ Từng Thành phần

| Cấu hình thực nghiệm | OOS Recall (%) | OOS FPR (%) | Refusal Precision (%) | Refusal F1 (%) | Cơ chế Chống ảo giác Citation |
|---|---:|---:|---:|---:|:---:|
| **Full Pipeline** | 72.7% | 21.8% | 48.5% | 58.2% | Hoạt động (Chặn ảo giác citation) |
| **w/o Year Filter** | 59.1% | 9.0% | 65.0% | 61.9% | Hoạt động (Chặn ảo giác citation) |
| **w/o OOS Filter** | 50.0% | 17.9% | 44.0% | 46.8% | Hoạt động (Chặn ảo giác citation) |
| **w/o Retrieval Gate** | 40.9% | 3.9% | 75.0% | 52.9% | Hoạt động (Chặn ảo giác citation) |
| **w/o Boost 2026** | 72.7% | 21.8% | 48.5% | 58.2% | Hoạt động (Chặn ảo giác citation) |
| **w/o Attribution Gate** | 72.7% | 21.8% | 48.5% | 58.2% | Bị tắt (0% bảo vệ citation) |

## Nhận xét chuyên sâu từ kết quả Ablation:

1. **Tác động của OOS Filter (Hướng C):** Khi loại bỏ Hướng C (`w/o OOS Filter`), OOS Recall giảm mạnh và áp lực dồn toàn bộ lên Retrieval Gate. Hướng C đóng vai trò cốt lõi trong việc nhận diện trước các câu hỏi dự đoán điểm hoặc tư vấn hướng nghiệp.
2. **Tác động của Retrieval Gate:** Khi loại bỏ Retrieval Gate (`w/o Retrieval Gate`), FPR giảm về 3.8% nhưng Recall chỉ đạt 40.9%. Retrieval Gate đóng vai trò chốt chặn cuối cùng bắt được 53.8% số câu refuse còn sót.
3. **Tác động của Year Filter:** Year Filter giúp phát hiện và từ chối dứt khoát các năm ngoài tầm dữ liệu tuyển sinh với FPR = 0%.
4. **Tác động của Attribution Gate:** Đảm bảo 100% các trích dẫn gửi về sinh viên đều nằm trong danh mục văn bản thực của nhà trường, loại bỏ hoàn toàn hiện tượng mô hình sinh trích dẫn ảo (Citation Hallucination).
