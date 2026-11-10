$repoRoot = Split-Path -Parent $PSScriptRoot
Write-Host "Starting GPTCraft Backend (port 8000) and Frontend (port 3000)..." -ForegroundColor Cyan

Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$repoRoot\backend'; if (Test-Path .\.venv\Scripts\python.exe) { .\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 } else { python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 }"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$repoRoot\frontend'; npm run dev"
