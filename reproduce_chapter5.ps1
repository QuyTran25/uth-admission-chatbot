# reproduce_chapter5.ps1 — Script PowerShell tái lập kết quả Chương 5 cho môi trường Windows
# Hỗ trợ Feedback #11 (Reproducibility)

param (
    [string]$Target = "reproduce"
)

$ErrorActionPreference = "Stop"

# Xác định Python thực thi (ưu tiên .venv)
$PythonExe = "python"
if (Test-Path ".venv\Scripts\python.exe") {
    $PythonExe = ".venv\Scripts\python.exe"
}
Write-Host "Sử dụng Python: $PythonExe" -ForegroundColor Cyan

function Run-PyTest {
    Write-Host "`n>>> [1/5] Chạy kiểm thử tự động (Unit Tests)..." -ForegroundColor Yellow
    & $PythonExe -m pytest backend/tests -v
}

function Run-LeakageCheck {
    Write-Host "`n>>> [2/5] Kiểm tra rò rỉ dữ liệu giữa Dev và Locked set..." -ForegroundColor Yellow
    & $PythonExe backend/eval/check_locked_overlap.py
}

function Run-Audit {
    Write-Host "`n>>> [3/5] Đối chiếu Gold Chunk với Index Canonical..." -ForegroundColor Yellow
    & $PythonExe backend/eval/audit_gold_chunks.py --dataset backend/data/test/test_questions_locked.csv
    & $PythonExe backend/eval/audit_gold_chunks.py --dataset backend/data/test/dev_questions.csv
}

function Run-EvalDev {
    Write-Host "`n>>> [4/5] Benchmark Retrieval Bảng 5.1 trên DEV SET (kèm Bootstrap CI & Paired Test)..." -ForegroundColor Yellow
    & $PythonExe backend/eval/run_retrieval_eval.py --dataset backend/data/test/dev_questions.csv --tag dev --protocol canonical_mapped
}

function Run-EvalLocked {
    Write-Host "`n>>> [5/5] Benchmark Retrieval Bảng 5.1 trên LOCKED SET (kèm Bootstrap CI & Paired Test)..." -ForegroundColor Yellow
    & $PythonExe backend/eval/run_retrieval_eval.py --dataset backend/data/test/test_questions_locked.csv --tag locked --protocol canonical_mapped
}

function Run-EvalOOS {
    Write-Host "`n>>> Đánh giá Khả năng Chặn Out-of-Scope (3 Lớp Hợp nhất)..." -ForegroundColor Yellow
    & $PythonExe backend/eval/pipeline_union_eval.py
}

switch ($Target.ToLower()) {
    "test" { Run-PyTest }
    "leakage-check" { Run-LeakageCheck }
    "audit" { Run-Audit }
    "eval-dev" { Run-EvalDev }
    "eval-locked" { Run-EvalLocked }
    "eval-oos" { Run-EvalOOS }
    "reproduce" {
        Run-PyTest
        Run-LeakageCheck
        Run-Audit
        Run-EvalDev
        Run-EvalLocked
        Write-Host "`n==========================================================" -ForegroundColor Green
        Write-Host "HOÀN TẤT TÁI LẬP KẾT QUẢ CHƯƠNG 5 THÀNH CÔNG!" -ForegroundColor Green
        Write-Host "Các báo cáo đã lưu tại thư mục backend/eval/results/" -ForegroundColor Green
        Write-Host "==========================================================" -ForegroundColor Green
    }
    default {
        Write-Host "Lệnh không hợp lệ: $Target" -ForegroundColor Red
        Write-Host "Các target khả dụng: test, leakage-check, audit, eval-dev, eval-locked, eval-oos, reproduce"
    }
}
