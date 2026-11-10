$ErrorActionPreference = "SilentlyContinue"
$repoRoot = Split-Path -Parent $PSScriptRoot
$branch = (git -C $repoRoot rev-parse --abbrev-ref HEAD 2>$null)
if (-not $branch) { $branch = "unknown" }

$msg = "GPTCraft Monorepo Harness Active (branch: $branch). Structure: backend/ (FastAPI + LangGraph) and frontend/ (React 19 + Vite). Use 'scripts/verify.ps1' or the 'gptcraft-verify' skill to validate full-stack changes."

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
