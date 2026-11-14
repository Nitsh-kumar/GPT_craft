$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$totalSteps = 7

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "  GPTCraft Full-Stack Verification Suite " -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan

# 1. Harness Drift Check
Write-Host "`n[1/$totalSteps] Running Harness Drift Check (scripts/check-harness.ps1)..." -ForegroundColor Yellow
$global:LASTEXITCODE = 0
& (Join-Path $PSScriptRoot "check-harness.ps1")
if ($LASTEXITCODE -and $LASTEXITCODE -ne 0) {
    throw "Harness drift check failed with exit code $LASTEXITCODE"
}
Write-Host "[OK] Harness drift check passed!" -ForegroundColor Green

# 2. Session Hook & Memory Helper Tests
Write-Host "`n[2/$totalSteps] Running Session Hook & Memory Helper Tests (scripts/test-session-hook.ps1)..." -ForegroundColor Yellow
$global:LASTEXITCODE = 0
& (Join-Path $PSScriptRoot "test-session-hook.ps1")
if ($LASTEXITCODE -and $LASTEXITCODE -ne 0) {
    throw "Session hook tests failed with exit code $LASTEXITCODE"
}
Write-Host "[OK] Session hook tests passed!" -ForegroundColor Green

# 3. Backend Verification
Write-Host "`n[3/$totalSteps] Running Backend Pytest Suite..." -ForegroundColor Yellow
Push-Location (Join-Path $repoRoot "backend")
try {
    $winVenvPython = Join-Path "." (Join-Path ".venv" (Join-Path "Scripts" "python.exe"))
    $posixVenvPython = Join-Path "." (Join-Path ".venv" (Join-Path "bin" "python"))
    if (Test-Path -LiteralPath $winVenvPython) {
        $pythonCmd = $winVenvPython
    } elseif (Test-Path -LiteralPath $posixVenvPython) {
        $pythonCmd = $posixVenvPython
    } else {
        $pythonCmd = "python"
    }
    & $pythonCmd -m pytest -v
    if ($LASTEXITCODE -ne 0) {
        throw "Backend pytest failed with exit code $LASTEXITCODE"
    }
    Write-Host "[OK] Backend tests passed!" -ForegroundColor Green
} finally {
    Pop-Location
}

# 4-7. Frontend Verification
Push-Location (Join-Path $repoRoot "frontend")
try {
    # 4. Frontend Unit Tests
    Write-Host "`n[4/$totalSteps] Running Frontend Unit Tests (npm run test:unit)..." -ForegroundColor Yellow
    npm run test:unit
    if ($LASTEXITCODE -ne 0) {
        throw "Frontend unit tests failed with exit code $LASTEXITCODE"
    }
    Write-Host "[OK] Frontend unit tests passed!" -ForegroundColor Green

    # 5. Frontend TypeScript Type-Check
    Write-Host "`n[5/$totalSteps] Running Frontend TypeScript Check (npm run lint)..." -ForegroundColor Yellow
    npm run lint
    if ($LASTEXITCODE -ne 0) {
        throw "Frontend TypeScript check failed with exit code $LASTEXITCODE"
    }
    Write-Host "[OK] Frontend TypeScript check passed!" -ForegroundColor Green

    # 6. Frontend Stream Tests
    Write-Host "`n[6/$totalSteps] Running Frontend Stream Tests (npm test)..." -ForegroundColor Yellow
    npm test
    if ($LASTEXITCODE -ne 0) {
        throw "Frontend stream tests failed with exit code $LASTEXITCODE"
    }
    Write-Host "[OK] Frontend stream tests passed!" -ForegroundColor Green

    # 7. Frontend Production Build
    Write-Host "`n[7/$totalSteps] Running Frontend Production Build (npm run build)..." -ForegroundColor Yellow
    npm run build
    if ($LASTEXITCODE -ne 0) {
        throw "Frontend Vite build failed with exit code $LASTEXITCODE"
    }
    Write-Host "[OK] Frontend build passed!" -ForegroundColor Green
} finally {
    Pop-Location
}

Write-Host "`n[PASS] All $totalSteps full-stack and harness verification checks passed!" -ForegroundColor Cyan
Write-Host "Optional locally (enforced in CI): cd frontend && npm run test:e2e" -ForegroundColor DarkGray
