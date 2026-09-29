# Báo cáo Đối chiếu Gold Chunk với Index Canonical — dev_questions.csv

> [!IMPORTANT]
**Tổng kết kiểm toán:**
- Tổng số câu hỏi: `390`
- Số câu hỏi cần Retrieval (In-scope + Year-control): `301`
- Số câu hỏi Out-of-scope (Không cần Retrieval, chỉ đo Refusal): `89`
- Số câu có Gold Chunk tồn tại trong Index (Valid): `291` (96.68%)
- Số câu có Gold Chunk KHÔNG tồn tại trong Index (Missing): `10` (3.32%)
- Số Chunk ID độc nhất bị thiếu: `5`
- Số câu có thể ánh xạ tự động sang chunk chuẩn (Canonical mapping): `1`

## 1. Danh sách Chunk ID không tồn tại trong Index

- `2023_diem-chuan_dai-hoc-chinh-quy_t000_r000`: xuất hiện ở 1 câu hỏi.
- `2024_diem-chuan_dai-hoc-chinh-quy_t000_r000`: xuất hiện ở 3 câu hỏi.
- `2025_diem-chuan_dai-hoc-chinh-quy_t000_r000`: xuất hiện ở 2 câu hỏi.
- `<EMPTY>`: xuất hiện ở 3 câu hỏi.
- `thong_tin_chung_2026_co-so_chunks`: xuất hiện ở 1 câu hỏi.

## 2. Chi tiết các câu hỏi bị lệch Gold Chunk & Ánh xạ khắc phục

| ID | Nhóm | Chunk ID cũ | Chunk ID chuẩn hóa | Câu hỏi |
|---|---|---|---|---|
| 10 | in_scope | `thong_tin_chung_2026_co-so_chunks` | `2026_diem-chuan_dai-hoc-chinh-quy_s065` | Trường có học ở Vũng Tàu không ad? Nằm ở đâu vậy? |
| 15 | year_control | `2025_diem-chuan_dai-hoc-chinh-quy_t000_r000` | `*Chưa ánh xạ*` | Cho em xin điểm chuẩn ngành Kỹ thuật điều khiển và tự động h |
| 16 | year_control | `2025_diem-chuan_dai-hoc-chinh-quy_t000_r000` | `*Chưa ánh xạ*` | Mình xin điểm ngành Quản trị kinh doanh năm 2025. |
| 17 | year_control | `2024_diem-chuan_dai-hoc-chinh-quy_t000_r000` | `*Chưa ánh xạ*` | Năm 2024 ngành Mạng máy tính thi THPT lấy điểm có cao không? |
| 18 | year_control | `2024_diem-chuan_dai-hoc-chinh-quy_t000_r000` | `*Chưa ánh xạ*` | Điểm thi đại học 2024 ngành Kỹ thuật ô tô là bao nhiêu vậy a |
| 19 | year_control | `2024_diem-chuan_dai-hoc-chinh-quy_t000_r000` | `*Chưa ánh xạ*` | Cho mình hỏi điểm chuẩn năm 2024 ngành Kinh tế vận tải (Hàng |
| 20 | year_control | `2023_diem-chuan_dai-hoc-chinh-quy_t000_r000` | `*Chưa ánh xạ*` | Hồi 2023 thì Logistics hệ Chất lượng cao lấy mấy điểm ạ? |
| 28 | year_control | `<EMPTY>` | `*Chưa ánh xạ*` | Trường có bảng điểm chuẩn năm 2020 không, cho em xin với. |
| 135 | in_scope | `<EMPTY>` | `*Chưa ánh xạ*` | Khối D07 gồm những môn gì vậy ạ? |
| 150 | year_control | `<EMPTY>` | `*Chưa ánh xạ*` | Em muốn xin lại thông tin điểm chuẩn thi đại học năm 2018 củ |

## 3. Khuyến nghị cho Đánh giá Retrieval (Chapter 5)

Để khắc phục trọn vẹn phản hồi của Giảng viên về việc MRR/Recall bị chặn trên nhân tạo:
1. **Protocol A (Raw):** Chạy đánh giá trên toàn bộ tập câu hỏi in-scope với Gold gốc. Báo cáo rõ trần Recall bị giảm do missing chunk.
2. **Protocol B (Valid Subset):** Báo cáo metric trên tập câu hỏi hợp lệ (`N = {res['valid_gold_count']}`) để đánh giá chính xác năng lực retriever.
3. **Protocol C (Canonical Mapped):** Ánh xạ các chunk `_r000` về dòng dữ liệu thực tế và tính toán lại toàn bộ Bảng 5.1.
