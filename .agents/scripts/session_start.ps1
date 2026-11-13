$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$branch = (& git -C $repoRoot rev-parse --abbrev-ref HEAD 2>$null)
if (-not $branch) { $branch = 'unknown' }
$memoryStatus = 'unavailable (manual helper remains available)'
. (Join-Path $PSScriptRoot 'memory_status.ps1')
$job = $null
if (Get-Command mem0 -ErrorAction SilentlyContinue) {
    try {
        # Bound memory lookup independently of the hook's overall timeout.
        $job = Start-Job -ScriptBlock {
            $output = mem0 --json search 'GPTCraft' 2>$null
            @{ code = $LASTEXITCODE; raw = ($output -join "`n") }
        }
        $finished = Wait-Job $job -Timeout 3
        if ($finished) {
            $result = Receive-Job $job -ErrorAction Stop
            $memoryStatus = ConvertTo-ProjectMemoryStatus -Raw $result.raw -ExitCode $result.code
        } else { $memoryStatus = 'lookup timed out (continuing without memory)' }
    } catch { $memoryStatus = 'lookup failed (continuing without memory)' }
    finally {
        if ($job) { Stop-Job $job -ErrorAction SilentlyContinue; Remove-Job $job -Force -ErrorAction SilentlyContinue }
    }
}
$msg = "GPTCraft harness active. Repository: $repoRoot; branch: $branch. Backend: backend/; frontend: frontend/. Run scripts/verify.ps1 before completion. Memory: $memoryStatus."
@{ injectSteps = @(@{ systemMessage = @{ systemMessage = $msg } }) } |
    ConvertTo-Json -Depth 5 -Compress
