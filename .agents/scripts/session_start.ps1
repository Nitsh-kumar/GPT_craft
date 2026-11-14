$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$branch = $null
try {
    $branchOutput = & git -C $repoRoot rev-parse --abbrev-ref HEAD 2>$null
    if ($LASTEXITCODE -eq 0 -and $branchOutput) {
        $branch = ($branchOutput | Select-Object -First 1).Trim()
    }
} catch {
    $branch = $null
}
if (-not $branch) { $branch = 'unknown' }

$memoryStatus = 'offline startup (use .agents/scripts/mem0_helper.ps1 manually if MEM0_USER_ID is configured)'
$msg = "GPTCraft harness active. Repository: $repoRoot; branch: $branch. Backend: backend/; frontend: frontend/. Run scripts/verify.ps1 before completion. Memory: $memoryStatus."
@{ injectSteps = @(@{ systemMessage = @{ systemMessage = $msg } }) } |
    ConvertTo-Json -Depth 5 -Compress
