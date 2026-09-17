# dev.ps1 - start backend then frontend after verified health
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$backend = Join-Path $root 'backend'
$frontend = Join-Path $root 'frontend'
$python = Join-Path $root '.venv\Scripts\python.exe'
$healthUrl = 'http://127.0.0.1:8000/api/v1/health'
$logDir = Join-Path $root 'logs'
$backendLog = Join-Path $logDir 'backend-dev.log'
$backendErrorLog = Join-Path $logDir 'backend-dev-error.log'
$frontendLog = Join-Path $logDir 'frontend-dev.log'
$frontendErrorLog = Join-Path $logDir 'frontend-dev-error.log'

function Stop-PortProcessTree {
  param([int]$Port)

  $owners = @(
    Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
      Select-Object -ExpandProperty OwningProcess -Unique
  )

  foreach ($owner in $owners) {
    Write-Host "Stopping process on port $Port (PID: $owner)" -ForegroundColor Yellow
    Stop-Process -Id $owner -Force -ErrorAction SilentlyContinue
  }

  for ($attempt = 1; $attempt -le 20; $attempt++) {
    $listener = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    if (-not $listener) { return }
    Start-Sleep -Milliseconds 300
  }

  throw "Port $Port is still occupied. Close the process using this port, then run .\dev.ps1 again."
}

Write-Host "Project root: $root" -ForegroundColor Cyan
if (-not (Test-Path $python)) { throw "Python virtual environment missing: $python" }
if (-not (Test-Path (Join-Path $root '.env'))) { throw 'Missing .env with GEMINI_API_KEY.' }
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir | Out-Null }

$frontendEnv = Join-Path $frontend '.env'
if (-not (Test-Path $frontendEnv)) {
  Set-Content -Path $frontendEnv -Value 'VITE_API_BASE_URL=http://localhost:8000' -Encoding utf8
}

Stop-PortProcessTree -Port 5173
Stop-PortProcessTree -Port 8000
Start-Sleep -Milliseconds 600

Write-Host 'Starting backend on port 8000...' -ForegroundColor Green
$backendProc = Start-Process -FilePath $python `
  -ArgumentList '-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '8000' `
  -WorkingDirectory $backend -PassThru -WindowStyle Hidden `
  -RedirectStandardOutput $backendLog -RedirectStandardError $backendErrorLog

$ready = $false
for ($attempt = 1; $attempt -le 45; $attempt++) {
  if ($backendProc.HasExited) {
    $log = if (Test-Path $backendLog) { Get-Content $backendLog -Tail 30 | Out-String } else { 'No backend log was created.' }
    throw "Backend exited during startup. Last log lines:`n$log"
  }
  try {
    $health = Invoke-WebRequest -Uri $healthUrl -Method Get -TimeoutSec 2 -UseBasicParsing -ErrorAction Stop
    if ($health.StatusCode -eq 200) { $ready = $true; break }
  } catch { }
  Start-Sleep -Seconds 2
}
if (-not $ready) {
  & taskkill.exe /PID $backendProc.Id /T /F | Out-Null
  throw "Backend did not become healthy in 90 seconds. See $backendLog"
}

Write-Host 'Backend health check passed.' -ForegroundColor Green
Write-Host 'Starting frontend on port 5173...' -ForegroundColor Green
$frontendProc = Start-Process -FilePath 'npm.cmd' -ArgumentList 'run', 'dev' `
  -WorkingDirectory $frontend -PassThru -WindowStyle Hidden `
  -RedirectStandardOutput $frontendLog -RedirectStandardError $frontendErrorLog

Write-Host 'Backend:  http://localhost:8000' -ForegroundColor Green
Write-Host 'Frontend: http://localhost:5173' -ForegroundColor Green
Write-Host 'Press Ctrl+C to stop both services.' -ForegroundColor Yellow

try {
  while ($true) {
    Start-Sleep -Seconds 1
    if ($backendProc.HasExited) {
      throw "Backend stopped unexpectedly. See $backendLog and $backendErrorLog"
    }
    if ($frontendProc.HasExited) {
      throw "Frontend stopped unexpectedly. See $frontendLog and $frontendErrorLog"
    }
  }
} finally {
  foreach ($child in @($backendProc, $frontendProc)) {
    if ($child -and -not $child.HasExited) {
      Stop-Process -Id $child.Id -Force -ErrorAction SilentlyContinue
    }
  }
}