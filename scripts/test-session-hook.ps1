$ErrorActionPreference = 'Stop'

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$expectedBranch = (& git -C $repoRoot rev-parse --abbrev-ref HEAD).Trim()
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($expectedBranch)) {
    throw 'Failed to determine expected git branch.'
}

$hooksPath = Join-Path $repoRoot ('.agents/hooks.json' -replace '/', [System.IO.Path]::DirectorySeparatorChar)
$config = Get-Content -LiteralPath $hooksPath -Raw | ConvertFrom-Json
$command = $config.'gptcraft-harness'.SessionStart[0].command
if ([string]::IsNullOrWhiteSpace($command)) {
    throw 'SessionStart hook command is missing in .agents/hooks.json.'
}

$shimDir = Join-Path ([System.IO.Path]::GetTempPath()) ("gptcraft-hook-test-" + [Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $shimDir -Force | Out-Null
$origPath = $env:PATH
$origMem0UserId = $env:MEM0_USER_ID
$hasOrigMem0UserId = Test-Path Env:MEM0_USER_ID

try {
    $shimLogJsonl = Join-Path $shimDir 'mem0_calls.jsonl'
    $shimLogCmd = Join-Path $shimDir 'mem0_cmd_calls.log'

    $mem0Ps1Content = @"
`$entry = @{ args = @(`$args) } | ConvertTo-Json -Compress
Add-Content -LiteralPath '$($shimLogJsonl -replace '''', '''''')' -Value `$entry
`$global:LASTEXITCODE = 0
"@
    Set-Content -LiteralPath (Join-Path $shimDir 'mem0.ps1') -Value $mem0Ps1Content -Encoding ASCII

    $mem0CmdContent = @"
@echo off
echo %*>> "$shimLogCmd"
exit /b 0
"@
    Set-Content -LiteralPath (Join-Path $shimDir 'mem0.cmd') -Value $mem0CmdContent -Encoding ASCII

    $env:PATH = "$shimDir$([System.IO.Path]::PathSeparator)$origPath"

    # 1. Verify SessionStart hook runs fast and offline from root and nested directories
    foreach ($directory in @($repoRoot, (Join-Path $repoRoot 'backend'))) {
        Push-Location $directory
        try {
            $sw = [System.Diagnostics.Stopwatch]::StartNew()
            $output = & cmd.exe /d /s /c $command
            $sw.Stop()
            if ($LASTEXITCODE -ne 0) {
                throw "Session hook failed from $directory with exit code $LASTEXITCODE"
            }
            if ($sw.Elapsed.TotalSeconds -ge 10) {
                throw "Session hook exceeded fast offline startup budget ($([math]::Round($sw.Elapsed.TotalSeconds, 2))s) from $directory"
            }

            $payload = ($output -join "`n") | ConvertFrom-Json
            $message = $payload.injectSteps[0].systemMessage.systemMessage
            if ([string]::IsNullOrWhiteSpace($message)) {
                throw "Session hook emitted empty systemMessage from $directory"
            }
            if (-not $message.Contains($repoRoot) -or -not $message.Contains("branch: $expectedBranch")) {
                throw "Session hook returned incorrect repository/branch context from ${directory}: $message"
            }
            if (-not $message.Contains('Memory:')) {
                throw "Memory status is missing in SessionStart output from $directory"
            }
            if ($message -match '(?i)lookup timed out|retrieved \d+ project facts') {
                throw "Session hook appears to have run a live startup Mem0 lookup: $message"
            }
            if ($message -notmatch '(?i)helper|manual|offline|unavailable|disabled|on-demand|mem0_helper') {
                throw "Session hook Memory status does not indicate offline/manual helper usage: $message"
            }
        } finally {
            Pop-Location
        }
    }

    if ((Test-Path -LiteralPath $shimLogJsonl) -or (Test-Path -LiteralPath $shimLogCmd)) {
        throw 'SessionStart hook invoked mem0 CLI instead of staying strictly offline.'
    }
    Write-Host 'Session hook emits valid offline context from root and nested directories.'

    # 2. Retain ConvertTo-ProjectMemoryStatus unit checks if memory_status.ps1 exists
    $memoryStatusPath = Join-Path $repoRoot ('.agents/scripts/memory_status.ps1' -replace '/', [System.IO.Path]::DirectorySeparatorChar)
    if (Test-Path -LiteralPath $memoryStatusPath -PathType Leaf) {
        . $memoryStatusPath
        $failure = ConvertTo-ProjectMemoryStatus -Raw '{"status":"error","data":[]}' -ExitCode 0
        if ($failure -notlike 'lookup failed*') { throw 'Structured memory failure reported as success' }
        $failure = ConvertTo-ProjectMemoryStatus -Raw '{"status":"success","data":[]}' -ExitCode 1
        if ($failure -notlike 'lookup failed*') { throw 'Nonzero CLI exit reported as success' }
        $success = ConvertTo-ProjectMemoryStatus -Raw '{"status":"success","data":[{"memory":"GPTCraft password=private-value"},{"memory":"Unrelated personal fact"}]}' -ExitCode 0
        if ($success -notlike 'retrieved 1 project facts*' -or $success.Contains('private-value')) {
            throw "Memory summary mismatch (expected one project fact, actual status: $success)"
        }
        Write-Host 'Memory diagnostics distinguish failures and never print raw facts.'
    }

    # 3. Validate mem0_helper.ps1 syntax, help metadata, and offline MEM0_USER_ID handling
    $mem0HelperPath = Join-Path $repoRoot ('.agents/scripts/mem0_helper.ps1' -replace '/', [System.IO.Path]::DirectorySeparatorChar)
    if (-not (Test-Path -LiteralPath $mem0HelperPath -PathType Leaf)) {
        throw 'Missing .agents/scripts/mem0_helper.ps1'
    }

    $tokens = $null
    $parseErrors = $null
    $null = [System.Management.Automation.Language.Parser]::ParseFile($mem0HelperPath, [ref]$tokens, [ref]$parseErrors)
    if ($parseErrors -and $parseErrors.Count -gt 0) {
        throw "PowerShell syntax error in mem0_helper.ps1: $($parseErrors[0].Message)"
    }

    $helpInfo = Get-Help $mem0HelperPath -ErrorAction Stop
    $helpText = ($helpInfo | Out-String)
    if ($helpText -match '(?i)\bnit2314\b') {
        throw 'mem0_helper.ps1 help metadata still contains hardcoded nit2314.'
    }

    # 3a. -Action help runs offline without error
    $global:LASTEXITCODE = 0
    $helpOutput = & $mem0HelperPath -Action help | Out-String
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($helpOutput)) {
        throw 'mem0_helper.ps1 -Action help failed or produced empty output.'
    }

    # Clear shim logs after help check
    Remove-Item -LiteralPath $shimLogJsonl -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $shimLogCmd -Force -ErrorAction SilentlyContinue

    # 3b. Missing MEM0_USER_ID behavior for user-scoped action (-Action list)
    Remove-Item Env:MEM0_USER_ID -ErrorAction SilentlyContinue
    $missingFailed = $false
    $missingMessage = ''
    try {
        $global:LASTEXITCODE = 0
        $null = & $mem0HelperPath -Action list 2>&1
        if ($LASTEXITCODE -ne 0) { $missingFailed = $true }
    } catch {
        $missingFailed = $true
        $missingMessage = $_.Exception.Message
    }

    if ($missingFailed) {
        if ((Test-Path -LiteralPath $shimLogJsonl) -or (Test-Path -LiteralPath $shimLogCmd)) {
            throw 'mem0_helper.ps1 invoked mem0 CLI even though MEM0_USER_ID was missing.'
        }
        if ($missingMessage -notmatch '(?i)MEM0_USER_ID|UserId|user scope') {
            throw "mem0_helper.ps1 failed on missing MEM0_USER_ID with unexpected message: $missingMessage"
        }
    } else {
        # If allowed to proceed without MEM0_USER_ID, ensure it neither used nit2314 nor passed an empty --user-id
        if (Test-Path -LiteralPath $shimLogJsonl) {
            $calls = Get-Content -LiteralPath $shimLogJsonl
            foreach ($c in $calls) {
                if ($c -match '(?i)nit2314') { throw 'mem0_helper.ps1 fell back to hardcoded nit2314.' }
                $parsedCall = $c | ConvertFrom-Json
                for ($idx = 0; $idx -lt $parsedCall.args.Count; $idx++) {
                    if ($parsedCall.args[$idx] -eq '--user-id' -and (($idx + 1) -ge $parsedCall.args.Count -or [string]::IsNullOrWhiteSpace([string]$parsedCall.args[$idx + 1]))) {
                        throw 'mem0_helper.ps1 passed empty --user-id when MEM0_USER_ID was missing.'
                    }
                }
            }
        }
    }

    # 3c. Configured MEM0_USER_ID passes --user-id cleanly to mock mem0 shim
    Remove-Item -LiteralPath $shimLogJsonl -Force -ErrorAction SilentlyContinue
    $env:MEM0_USER_ID = 'harness-test-user'
    $global:LASTEXITCODE = 0
    & $mem0HelperPath -Action list | Out-Null
    if (-not (Test-Path -LiteralPath $shimLogJsonl)) {
        throw 'mem0_helper.ps1 -Action list did not invoke mem0 when MEM0_USER_ID was set.'
    }
    $listCall = (Get-Content -LiteralPath $shimLogJsonl | Select-Object -Last 1) | ConvertFrom-Json
    if ($listCall.args -notcontains 'list' -or $listCall.args -notcontains '--user-id' -or $listCall.args -notcontains 'harness-test-user') {
        throw "mem0_helper.ps1 -Action list passed unexpected arguments: $($listCall.args -join ' ')"
    }

    # 3d. Explicit -UserId overrides unset MEM0_USER_ID cleanly
    Remove-Item -LiteralPath $shimLogJsonl -Force -ErrorAction SilentlyContinue
    Remove-Item Env:MEM0_USER_ID -ErrorAction SilentlyContinue
    $global:LASTEXITCODE = 0
    & $mem0HelperPath -Action search -QueryOrText 'architecture' -UserId 'explicit-user' -Json | Out-Null
    $searchCall = (Get-Content -LiteralPath $shimLogJsonl | Select-Object -Last 1) | ConvertFrom-Json
    if ($searchCall.args -notcontains '--json' -or $searchCall.args -notcontains 'search' -or $searchCall.args -notcontains 'architecture' -or $searchCall.args -notcontains 'explicit-user') {
        throw "mem0_helper.ps1 -Action search passed unexpected arguments: $($searchCall.args -join ' ')"
    }

    Write-Host 'mem0_helper.ps1 syntax, help metadata, and offline MEM0_USER_ID checks passed.'
} finally {
    $env:PATH = $origPath
    if ($hasOrigMem0UserId) {
        $env:MEM0_USER_ID = $origMem0UserId
    } else {
        Remove-Item Env:MEM0_USER_ID -ErrorAction SilentlyContinue
    }
    Remove-Item -LiteralPath $shimDir -Recurse -Force -ErrorAction SilentlyContinue
    $global:LASTEXITCODE = 0
}
