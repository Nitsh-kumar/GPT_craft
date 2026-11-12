$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "  GPTCraft Full-Stack Verification Suite " -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan

# 1. Backend Verification
Write-Host "`n[1/4] Running Backend Pytest Suite..." -ForegroundColor Yellow
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

# 2. Frontend Verification
Push-Location "$repoRoot\frontend"
try {
    # 2. Frontend Unit Tests
    Write-Host "`n[2/4] Running Frontend Unit Tests (npm run test:unit)..." -ForegroundColor Yellow
    npm run test:unit
    if ($LASTEXITCODE -ne 0) {
        throw "Frontend unit tests failed with exit code $LASTEXITCODE"
    }
    Write-Host "✅ Frontend unit tests passed!" -ForegroundColor Green

    # 3. Frontend TypeScript Type-Check
    Write-Host "`n[3/4] Running Frontend TypeScript Check (npm run lint)..." -ForegroundColor Yellow
    npm run lint
    if ($LASTEXITCODE -ne 0) {
        throw "Frontend TypeScript check failed with exit code $LASTEXITCODE"
    }
    Write-Host "✅ Frontend TypeScript check passed!" -ForegroundColor Green

    # 4. Frontend Production Build
    Write-Host "`n[4/4] Running Frontend Production Build (npm run build)..." -ForegroundColor Yellow
    npm run build
    if ($LASTEXITCODE -ne 0) {
        throw "Frontend Vite build failed with exit code $LASTEXITCODE"
    }
    Write-Host "✅ Frontend build passed!" -ForegroundColor Green
} finally {
    Pop-Location
}

Write-Host "`n🎉 All full-stack checks passed successfully!" -ForegroundColor Cyan
