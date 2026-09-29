# Makefile — Tái tạo kết quả toàn bộ thực nghiệm Luận văn UTH Admission Chatbot
# Hỗ trợ Feedback #11 của Giảng viên về tính Reproducibility

ifeq ($(OS),Windows_NT)
    PYTHON ?= $(if $(wildcard .venv/Scripts/python.exe),.venv/Scripts/python.exe,python)
else
    PYTHON ?= $(if $(wildcard .venv/bin/python),.venv/bin/python,python3)
endif

.PHONY: help test leakage-check audit eval-dev eval-locked eval-oos reproduce

help:
	@echo "Danh sách lệnh tái tạo thực nghiệm Chương 5:"
	@echo "  make test          - Chạy toàn bộ 21+ unit tests (PyTest)"
	@echo "  make leakage-check - Kiểm tra rò rỉ dữ liệu giữa Dev và Locked set"
	@echo "  make audit         - Đối chiếu Gold Chunks với Index canonical"
	@echo "  make eval-dev      - Chạy benchmark Retrieval Bảng 5.1 trên Dev Set"
	@echo "  make eval-locked   - Chạy benchmark Retrieval Bảng 5.1 trên Locked Set"
	@echo "  make eval-oos      - Đánh giá khả năng chặn OOS 3 lớp (Union Eval)"
	@echo "  make reproduce     - Chạy toàn bộ quy trình tái lập kết quả"

test:
	$(PYTHON) -m pytest backend/tests -v

leakage-check:
	$(PYTHON) backend/eval/check_locked_overlap.py

audit:
	$(PYTHON) backend/eval/audit_gold_chunks.py --dataset backend/data/test/test_questions_locked.csv
	$(PYTHON) backend/eval/audit_gold_chunks.py --dataset backend/data/test/dev_questions.csv

eval-dev:
	$(PYTHON) backend/eval/run_retrieval_eval.py --dataset backend/data/test/dev_questions.csv --tag dev --protocol canonical_mapped

eval-locked:
	$(PYTHON) backend/eval/run_retrieval_eval.py --dataset backend/data/test/test_questions_locked.csv --tag locked --protocol canonical_mapped

eval-oos:
	$(PYTHON) backend/eval/pipeline_union_eval.py

reproduce: test leakage-check audit eval-dev eval-locked
	@echo "=========================================================="
	@echo "Hoàn tất tái tạo toàn bộ thực nghiệm Chương 5!"
	@echo "Báo cáo xem tại backend/eval/results/"
	@echo "=========================================================="
