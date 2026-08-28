import os
import sys
import pandas as pd
import numpy as np

# Đường dẫn file
DATA_DIR = r"d:\uth-admission-chatbot\backend\data\test"
INPUT_CSV = os.path.join(DATA_DIR, "test_questions.csv")
DEV_CSV = os.path.join(DATA_DIR, "dev_questions.csv")
TEST_LOCKED_CSV = os.path.join(DATA_DIR, "test_questions_locked.csv")

# 9 câu hỏi có gap ID để theo dõi
GAP_IDS = {10, 13, 14, 15, 16, 17, 18, 19, 20}

def main():
    if not os.path.exists(INPUT_CSV):
        print(f"Lỗi: Không tìm thấy file {INPUT_CSV}")
        sys.exit(1)

    df = pd.read_csv(INPUT_CSV, encoding="utf-8")
    print(f"Tổng số câu hỏi ban đầu: {len(df)}")

    # Tạo nhãn phân tầng bằng cách kết hợp category và expected_behavior
    # Điền giá trị trống bằng "unknown" nếu có
    df['category'] = df['category'].fillna('unknown')
    df['expected_behavior'] = df['expected_behavior'].fillna('unknown')
    df['stratify_label'] = df['category'].astype(str) + "___" + df['expected_behavior'].astype(str)

    dev_rows = []
    test_rows = []

    # Thực hiện stratified split thủ công sử dụng seed 42
    # Nhóm theo stratify_label
    groups = df.groupby('stratify_label')
    for label, group in groups:
        # Xáo trộn dòng trong nhóm với seed cố định là 42
        shuffled_group = group.sample(frac=1, random_state=42).reset_index(drop=True)
        n_total = len(shuffled_group)
        
        # Tính số lượng câu cho tập test locked (20%)
        # Tối thiểu 1 câu nếu nhóm có từ 2 câu trở lên để đảm bảo phân tầng đều
        n_test = int(np.round(n_total * 0.2))
        if n_test == 0 and n_total >= 2:
            n_test = 1
            
        n_dev = n_total - n_test

        group_dev = shuffled_group.iloc[:n_dev]
        group_test = shuffled_group.iloc[n_dev:]

        dev_rows.append(group_dev)
        test_rows.append(group_test)

    # Ghép lại thành dataframe hoàn chỉnh
    df_dev = pd.concat(dev_rows, ignore_index=True)
    df_test = pd.concat(test_rows, ignore_index=True)

    # Xóa cột phụ stratify_label trước khi lưu
    df_dev = df_dev.drop(columns=['stratify_label'])
    df_test = df_test.drop(columns=['stratify_label'])

    # Sắp xếp lại theo id cho đẹp
    df_dev = df_dev.sort_values(by='id').reset_index(drop=True)
    df_test = df_test.sort_values(by='id').reset_index(drop=True)

    # Lưu file
    df_dev.to_csv(DEV_CSV, index=False, encoding="utf-8-sig")
    df_test.to_csv(TEST_LOCKED_CSV, index=False, encoding="utf-8-sig")

    print("\n=== THỐNG KÊ PHÂN CHIA (Stratified Split 80/20) ===")
    print(f"Tập Hiệu chỉnh (Dev Set): {len(df_dev)} câu ({len(df_dev)/len(df)*100:.1f}%)")
    print(f"Tập Kiểm thử Khóa (Locked Test Set): {len(df_test)} câu ({len(df_test)/len(df)*100:.1f}%)")

    # In phân bố chi tiết của từng nhãn để kiểm tra
    print("\nChi tiết phân bố theo Category & Expected Behavior:")
    print(f"{'Label (Category | Behavior)':<50} | {'Tổng':<6} | {'Dev':<6} | {'Test Locked':<12}")
    print("-" * 82)
    
    dev_counts = df_dev.groupby(['category', 'expected_behavior']).size().to_dict()
    test_counts = df_test.groupby(['category', 'expected_behavior']).size().to_dict()
    total_counts = df.groupby(['category', 'expected_behavior']).size().to_dict()

    for key in sorted(total_counts.keys()):
        label_str = f"{key[0]} | {key[1]}"
        tot = total_counts[key]
        dev_c = dev_counts.get(key, 0)
        test_c = test_counts.get(key, 0)
        print(f"{label_str:<50} | {tot:<6} | {dev_c:<6} | {test_c:<12}")

    # Kiểm tra phân bố của 9 câu gap ID đặc biệt
    print("\nPhân bố 9 câu hỏi đặc biệt có 'gap ID':")
    dev_gap_ids = set(df_dev[df_dev['id'].isin(GAP_IDS)]['id'].tolist())
    test_gap_ids = set(df_test[df_test['id'].isin(GAP_IDS)]['id'].tolist())
    
    print(f"  Nằm trong tập Dev ({len(dev_gap_ids)} câu): {sorted(list(dev_gap_ids))}")
    print(f"  Nằm trong tập Test Locked ({len(test_gap_ids)} câu): {sorted(list(test_gap_ids))}")

if __name__ == "__main__":
    main()
