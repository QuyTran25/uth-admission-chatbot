# dev.ps1 — chay dong thoi backend + frontend, tat he thong khi nhan Ctrl+C
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Write-Host "==> Thu muc goc: $root" -ForegroundColor Cyan

# Tat server cu neu con
foreach ($p in 5173, 8000) {
  $proc = Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique
  if ($proc) {
    Write-Host "==> Tat tien trinh cu o port $p (PID: $($proc -join ', '))" -ForegroundColor Yellow
    $proc | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }
  }
}

# Kiem tra .env goc
$envFile = Join-Path $root ".env"
if (-not (Test-Path $envFile)) {
  Write-Host "[!] Khong tim thay $envFile. Tao moi va them GEMINI_API_KEY." -ForegroundColor Red
  exit 1
}

# Kiem tra frontend/.env
$feEnv = Join-Path $root "frontend\.env"
if (-not (Test-Path $feEnv)) {
  Set-Content -Path $feEnv -Value "VITE_API_BASE_URL=http://localhost:8000"
}

$backend = Join-Path $root "backend"
$frontend = Join-Path $root "frontend"
$venvPy = Join-Path $root ".venv\Scripts\python.exe"

Write-Host "==> Khoi dong backend (uvicorn :8000)..." -ForegroundColor Green
$backendProc = Start-Process -FilePath $venvPy -ArgumentList "-m","uvicorn","app.main:app","--reload","--port","8000" -WorkingDirectory $backend -PassThru -WindowStyle Hidden

Write-Host "==> Khoi dong frontend (vite :5173)..." -ForegroundColor Green
$frontendProc = Start-Process -FilePath "npm.cmd" -ArgumentList "run","dev" -WorkingDirectory $frontend -PassThru -WindowStyle Hidden

Write-Host ""
Write-Host "Backend  -> http://localhost:8000" -ForegroundColor Green
Write-Host "Frontend -> http://localhost:5173" -ForegroundColor Green
Write-Host "Nhan Ctrl+C de dung ca hai." -ForegroundColor Yellow

try {
  while ($true) {
    Start-Sleep -Seconds 1
    if ($backendProc.HasExited) { Write-Host "[backend] Da tat." -ForegroundColor Red; break }
    if ($frontendProc.HasExited) { Write-Host "[frontend] Da tat." -ForegroundColor Red; break }
  }
} finally {
  foreach ($p in @($backendProc, $frontendProc)) {
    if ($p -and -not $p.HasExited) { Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue }
  }
}
