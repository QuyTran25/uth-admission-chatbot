"""check_locked_overlap.py — Kiểm tra bao nhiêu ID đã được phân tích chi tiết
thuộc test_questions_locked.csv (tập khóa) vs dev_questions.csv."""

import pandas as pd

locked = pd.read_csv(r'd:\uth-admission-chatbot\backend\data\test\test_questions_locked.csv')
dev    = pd.read_csv(r'd:\uth-admission-chatbot\backend\data\test\dev_questions.csv')

locked_ids = set(locked['id'].tolist())
dev_ids    = set(dev['id'].tolist())

# IDs đã được đọc/phân tích nội dung cụ thể trong tất cả các lượt phân tích
analyzed_fp_ids    = [11, 24, 25, 51, 139, 153, 256, 296, 303, 304, 368, 403, 426, 427]
analyzed_miss_ids  = [30, 40, 84, 86, 147, 236, 237, 242, 244, 248, 249, 250, 285, 286,
                      328, 329, 383, 385, 389, 392, 441, 443, 471, 472, 473, 474, 475,
                      476, 477, 478, 480, 481, 500]
analyzed_fp2_ids   = [20, 24, 28, 153, 289, 296, 368, 386, 426, 427]
analyzed_miss2_ids = [31, 37, 39, 40, 86, 92, 95, 141, 147, 242, 244, 248, 249, 295,
                      338, 339, 390, 393, 396, 397, 398, 400, 441, 443, 445, 471, 472,
                      473, 475, 478, 480, 481, 500]

all_analyzed = set(analyzed_fp_ids + analyzed_miss_ids +
                   analyzed_fp2_ids + analyzed_miss2_ids)

in_locked = sorted(all_analyzed & locked_ids)
in_dev    = sorted(all_analyzed & dev_ids)
unknown   = sorted(all_analyzed - locked_ids - dev_ids)

print(f"Tổng ID đã phân tích nội dung cụ thể : {len(all_analyzed)}")
print(f"Thuộc test_questions_locked.csv       : {len(in_locked)} ID  ← LEAKAGE")
print(f"Thuộc dev_questions.csv               : {len(in_dev)} ID  (an toàn)")
print(f"Không thuộc cả 2 (outlier)            : {len(unknown)} ID  {unknown}")
print()
print(f"Locked set: {len(locked_ids)} câu  |  Dev set: {len(dev_ids)} câu")
print()

if in_locked:
    print(f"=== {len(in_locked)} ID ĐÃ NHÌN THẤY THUỘC LOCKED SET ===")
    for qid in in_locked:
        row = locked[locked['id'] == qid].iloc[0]
        beh = row['expected_behavior']
        q   = str(row['user_query'])[:70]
        cat = row['category']
        print(f"  ID={qid:3d}  [{beh:18s}]  cat={cat}  |  {q}")
else:
    print("✅ Không có ID nào thuộc locked set — không có rò rỉ dữ liệu.")

print()
print("=== Các ID thuộc DEV SET (an toàn để tiếp tục) ===")
for qid in in_dev:
    row = dev[dev['id'] == qid].iloc[0]
    beh = row['expected_behavior']
    q   = str(row['user_query'])[:65]
    print(f"  ID={qid:3d}  [{beh:18s}]  {q}")
