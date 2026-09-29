# Báo cáo Đối chiếu Gold Chunk với Index Canonical — test_questions_locked.csv

> [!IMPORTANT]
**Tổng kết kiểm toán:**
- Tổng số câu hỏi: `100`
- Số câu hỏi cần Retrieval (In-scope + Year-control): `78`
- Số câu hỏi Out-of-scope (Không cần Retrieval, chỉ đo Refusal): `22`
- Số câu có Gold Chunk tồn tại trong Index (Valid): `69` (88.46%)
- Số câu có Gold Chunk KHÔNG tồn tại trong Index (Missing): `9` (11.54%)
- Số Chunk ID độc nhất bị thiếu: `4`
- Số câu có thể ánh xạ tự động sang chunk chuẩn (Canonical mapping): `9`

## 1. Danh sách Chunk ID không tồn tại trong Index

- `2023_diem-chuan_dai-hoc-chinh-quy_t000_r000`: xuất hiện ở 1 câu hỏi.
- `2024_diem-chuan_dai-hoc-chinh-quy_t000_r000`: xuất hiện ở 3 câu hỏi.
- `2025_diem-chuan_dai-hoc-chinh-quy_t000_r000`: xuất hiện ở 4 câu hỏi.
- `thong_tin_chung_2026_co-so_chunks`: xuất hiện ở 1 câu hỏi.

## 2. Chi tiết các câu hỏi bị lệch Gold Chunk & Ánh xạ khắc phục

| ID | Nhóm | Chunk ID cũ | Chunk ID chuẩn hóa | Câu hỏi |
|---|---|---|---|---|
| 10 | in_scope | `thong_tin_chung_2026_co-so_chunks` | `2026_diem-chuan_dai-hoc-chinh-quy_s065` | Trường có cơ sở đào tạo tại Vũng Tàu không ạ? Nếu có thì địa |
| 13 | year_control | `2025_diem-chuan_dai-hoc-chinh-quy_t000_r000` | `2025_diem-chuan_dai-hoc-chinh-quy_t000_r002` | Điểm trúng tuyển ngành Ngôn ngữ Anh của trường năm 2025 là b |
| 14 | year_control | `2025_diem-chuan_dai-hoc-chinh-quy_t000_r000` | `2025_diem-chuan_dai-hoc-chinh-quy_t000_r013` | Năm 2025, chương trình Công nghệ thông tin tiên tiến có mức  |
| 15 | year_control | `2025_diem-chuan_dai-hoc-chinh-quy_t000_r000` | `2025_diem-chuan_dai-hoc-chinh-quy_t001_r007` | Ngành Kỹ thuật điều khiển và tự động hóa năm 2025 có điểm tr |
| 16 | year_control | `2025_diem-chuan_dai-hoc-chinh-quy_t000_r000` | `2025_diem-chuan_dai-hoc-chinh-quy_t000_r005` | Cho em hỏi mức điểm chuẩn của ngành Quản trị kinh doanh năm  |
| 17 | year_control | `2024_diem-chuan_dai-hoc-chinh-quy_t000_r000` | `2024_diem-chuan_dai-hoc-chinh-quy_t000_r006` | Năm 2024, ngành Mạng máy tính lấy bao nhiêu điểm theo phương |
| 18 | year_control | `2024_diem-chuan_dai-hoc-chinh-quy_t000_r000` | `2024_diem-chuan_dai-hoc-chinh-quy_t000_r014` | Điểm chuẩn xét tuyển bằng kết quả thi THPT của ngành Kỹ thuậ |
| 19 | year_control | `2024_diem-chuan_dai-hoc-chinh-quy_t000_r000` | `2024_diem-chuan_dai-hoc-chinh-quy_t000_r034` | Ngành Kinh tế vận tải chuyên ngành Hàng không có điểm chuẩn  |
| 20 | year_control | `2023_diem-chuan_dai-hoc-chinh-quy_t000_r000` | `2023_diem-chuan_dai-hoc-chinh-quy_txt_s001` | Năm 2023, ngành Logistics chương trình Chất lượng cao có điể |

## 3. Khuyến nghị cho Đánh giá Retrieval (Chapter 5)

Để khắc phục trọn vẹn phản hồi của Giảng viên về việc MRR/Recall bị chặn trên nhân tạo:
1. **Protocol A (Raw):** Chạy đánh giá trên toàn bộ tập câu hỏi in-scope với Gold gốc. Báo cáo rõ trần Recall bị giảm do missing chunk.
2. **Protocol B (Valid Subset):** Báo cáo metric trên tập câu hỏi hợp lệ (`N = {res['valid_gold_count']}`) để đánh giá chính xác năng lực retriever.
3. **Protocol C (Canonical Mapped):** Ánh xạ các chunk `_r000` về dòng dữ liệu thực tế và tính toán lại toàn bộ Bảng 5.1.
