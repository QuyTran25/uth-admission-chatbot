# Baseline and Audit Report — Phase 0

## 1. Kết quả Audit hai thư mục Index

- **`backend/data/index/` (ROOT)**:
  - 725 chunks (FAISS d=768, 725 docs BM25).
  - Chưa được track bởi Git (chỉ có `.gitkeep`).
  - Khi đối chiếu với 216 unique gold `chunk_id` trong `test_questions.csv`: thiếu đúng **4 chunk IDs** (ảnh hưởng **9 câu hỏi**).
  - Đây chính là tập số liệu mà báo cáo cũ `retrieval_eval_report.md` đã dùng khi ghi chú `MISSING_CHUNKS = 4`.

- **`backend/backend/data/index/` (NESTED)**:
  - 679 chunks (FAISS d=768, 679 docs BM25).
  - Được commit và track trực tiếp trên Git repo từ commit `5e0e7c2`.
  - Khi đối chiếu với `test_questions.csv`: thiếu đúng **22 chunk IDs** (ảnh hưởng **35 câu hỏi**).
  - **Khớp 100% với phản biện của Giảng viên**: Giảng viên clone repository về và chạy trên index được track trên git, do đó phát hiện chính xác 35/393 câu hỏi thiếu 22 chunk ID.

## 2. Xác nhận Data Leakage lịch sử

- Toàn bộ 486 câu hỏi trong `test_questions.csv` (gồm 390 câu dev và 96 câu locked cũ) đã được chạy lặp đi lặp lại trong các script:
  - `run_retrieval_eval.py`
  - `direction_c_eval.py`
  - `tune_retrieval_gate.py`
- Tệp `check_locked_overlap.py` đã chỉ ra rõ 14 câu locked bị rò rỉ vào phân tích lỗi trực tiếp.
- Do đó, toàn bộ số liệu đánh giá cũ được dán nhãn: **`INVALID_FOR_FINAL_GENERALIZATION`**.
- Tập 486 câu này chính thức chuyển thành **`legacy_dev`**, chỉ dùng để hỗ trợ development và kiểm thử regression.
- Đánh giá năng lực tổng quát cuối cùng bắt buộc phải dùng bộ test mới `locked_v2` (mục tiêu 150 câu).

## 3. Vị trí sao lưu an toàn

- Bản sao nguyên vẹn của cả hai index cũ đã được lưu tại: `artifacts/baseline/backup_indexes/`.
- Manifest chi tiết từng file và SHA-256 lưu tại: `artifacts/baseline/index_audit.json`.
