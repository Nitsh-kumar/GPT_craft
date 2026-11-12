$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$expectedBranch = (& git -C $repoRoot rev-parse --abbrev-ref HEAD).Trim()
$config = Get-Content (Join-Path $repoRoot '.agents/hooks.json') -Raw | ConvertFrom-Json
$command = $config.'gptcraft-harness'.SessionStart[0].command
foreach ($directory in @($repoRoot, (Join-Path $repoRoot 'backend'))) {
    Push-Location $directory
    try {
        $output = & cmd.exe /d /s /c $command
        if ($LASTEXITCODE -ne 0) { throw "Session hook failed from $directory" }
        $payload = ($output -join "`n") | ConvertFrom-Json
        $message = $payload.injectSteps[0].systemMessage.systemMessage
        if (-not $message.Contains($repoRoot) -or -not $message.Contains("branch: $expectedBranch")) {
            throw 'Session hook returned incorrect repository/branch context'
        }
        if (-not $message.Contains('Memory:')) { throw 'Memory status is missing' }
    } finally { Pop-Location }
}
Write-Host 'Session hook emits valid context from root and nested directories.'

. (Join-Path $repoRoot '.agents/scripts/memory_status.ps1')
$failure = ConvertTo-ProjectMemoryStatus -Raw '{"status":"error","data":[]}' -ExitCode 0
if ($failure -notlike 'lookup failed*') { throw 'Structured memory failure reported as success' }
$failure = ConvertTo-ProjectMemoryStatus -Raw '{"status":"success","data":[]}' -ExitCode 1
if ($failure -notlike 'lookup failed*') { throw 'Nonzero CLI exit reported as success' }
$success = ConvertTo-ProjectMemoryStatus -Raw '{"status":"success","data":[{"memory":"GPTCraft password=private-value"},{"memory":"Unrelated personal fact"}]}' -ExitCode 0
if ($success -notlike 'retrieved 1 project facts*' -or $success.Contains('private-value')) {
    throw 'Memory summary leaked text or included unrelated facts'
}
Write-Host 'Memory diagnostics distinguish failures and never print raw facts.'
