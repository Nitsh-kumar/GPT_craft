$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "  GPTCraft Full-Stack Verification Suite " -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan

# 1. Backend Verification
Write-Host "`n[1/3] Running Backend Pytest Suite..." -ForegroundColor Yellow
Push-Location "$repoRoot\backend"
try {
    if (Test-Path ".\.venv\Scripts\python.exe") {
        $pythonCmd = ".\.venv\Scripts\python.exe"
    } else {
        $pythonCmd = "python"
    }
    & $pythonCmd -m pytest -v
    if ($LASTEXITCODE -ne 0) {
        throw "Backend pytest failed with exit code $LASTEXITCODE"
    }
    Write-Host "✅ Backend tests passed!" -ForegroundColor Green
} finally {
    Pop-Location
}

# 2. Frontend TypeScript Type-Check
Write-Host "`n[2/3] Running Frontend TypeScript Check (npm run lint)..." -ForegroundColor Yellow
Push-Location "$repoRoot\frontend"
try {
    npm run lint
    if ($LASTEXITCODE -ne 0) {
        throw "Frontend TypeScript check failed with exit code $LASTEXITCODE"
    }
    Write-Host "✅ Frontend TypeScript check passed!" -ForegroundColor Green

    # 3. Frontend Production Build
    Write-Host "`n[3/3] Running Frontend Production Build (npm run build)..." -ForegroundColor Yellow
    npm run build
    if ($LASTEXITCODE -ne 0) {
        throw "Frontend Vite build failed with exit code $LASTEXITCODE"
    }
    Write-Host "✅ Frontend build passed!" -ForegroundColor Green
} finally {
    Pop-Location
}

Write-Host "`n🎉 All full-stack checks passed successfully!" -ForegroundColor Cyan
