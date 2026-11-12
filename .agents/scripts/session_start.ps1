$ErrorActionPreference = "SilentlyContinue"
$repoRoot = Split-Path -Parent $PSScriptRoot
$branch = (git -C $repoRoot rev-parse --abbrev-ref HEAD 2>$null)
if (-not $branch) { $branch = "unknown" }

$msg = "GPTCraft Monorepo Harness Active (branch: $branch). Structure: backend/ (FastAPI + LangGraph) and frontend/ (React 19 + Vite). Active Spec: 'docs/specs/personal_agent_platform_spec.md'. Status: 'docs/PROJECT_STATUS.md'. Use 'scripts/verify.ps1' or the 'gptcraft-verify' skill to validate full-stack changes."

try {
  $rawMem = mem0 --json list 2>$null
  if ($rawMem) {
    $parsed = ($rawMem | ConvertFrom-Json)
    if ($parsed.status -eq "success" -and $parsed.data -and $parsed.data.Count -gt 0) {
      $facts = ($parsed.data | Select-Object -First 5 | ForEach-Object { "- $($_.memory)" }) -join "`n"
      $msg += "`n`nActive Mem0 Long-Term Memories (user: $($parsed.scope.user_id)):`n$facts"
    }
  }
} catch {
  # Non-blocking graceful degradation
}

$payload = @{
  injectSteps = @(
    @{
      systemMessage = @{
        systemMessage = $msg
      }
    }
  )
} | ConvertTo-Json -Depth 5 -Compress

Write-Output $payload
