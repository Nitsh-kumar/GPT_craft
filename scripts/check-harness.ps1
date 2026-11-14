$ErrorActionPreference = 'Stop'

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$failures = New-Object 'System.Collections.Generic.List[string]'

function Add-HarnessFailure {
    param([string]$Message)
    $script:failures.Add($Message) | Out-Null
}

function ConvertTo-RepoRelativePath {
    param([string]$FullPath)
    $rel = $FullPath
    if ($rel.StartsWith($repoRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
        $rel = $rel.Substring($repoRoot.Length).TrimStart('\', '/')
    }
    return ($rel -replace '\\', '/')
}

function Remove-LeadingDotSlash {
    param([string]$Value)
    $v = ($Value -replace '\\', '/').Trim()
    while ($v.StartsWith('./')) {
        $v = $v.Substring(2)
    }
    return $v
}

function Split-CommandTokens {
    param([string]$Text)
    $tokens = New-Object 'System.Collections.Generic.List[string]'
    foreach ($m in [regex]::Matches($Text, '''[^'']*''|"[^"]*"|\S+')) {
        $tokens.Add($m.Value) | Out-Null
    }
    return $tokens
}

function Test-RepoOrDocPathExists {
    param(
        [string]$CandidatePath,
        [string[]]$BaseDirs
    )
    $normalized = ($CandidatePath -replace '\\', '/').Trim()
    if ([string]::IsNullOrWhiteSpace($normalized)) { return $true }

    foreach ($baseDir in $BaseDirs) {
        if ([string]::IsNullOrWhiteSpace($baseDir)) { continue }
        $segments = $normalized -split '/'
        $joined = $baseDir
        foreach ($seg in $segments) {
            if ([string]::IsNullOrEmpty($seg) -or $seg -eq '.') { continue }
            $joined = Join-Path $joined $seg
        }
        try {
            if (Test-Path -LiteralPath $joined) {
                return $true
            }
        } catch {
            # Ignore invalid path character checks and continue trying base directories.
        }
    }
    return $false
}

function Get-NonCodeMarkdownLines {
    param([string[]]$Lines)
    $result = New-Object 'System.Collections.Generic.List[object]'
    $inFence = $false
    $fenceChar = ''
    $fenceLen = 0

    for ($i = 0; $i -lt $Lines.Count; $i++) {
        $line = $Lines[$i]
        $trimmed = $line.TrimStart()
        if ($trimmed -match '^([`~]{3,})(.*)$') {
            $marker = $Matches[1]
            $char = $marker.Substring(0, 1)
            $len = $marker.Length
            if (-not $inFence) {
                $inFence = $true
                $fenceChar = $char
                $fenceLen = $len
                continue
            } elseif ($char -eq $fenceChar -and $len -ge $fenceLen -and [string]::IsNullOrWhiteSpace($Matches[2])) {
                $inFence = $false
                $fenceChar = ''
                $fenceLen = 0
                continue
            }
        }

        if (-not $inFence) {
            $result.Add([PSCustomObject]@{
                LineNumber = $i + 1
                Text       = $line
            }) | Out-Null
        }
    }
    return $result
}

function Get-MarkdownCodeSnippets {
    param([string[]]$Lines)
    $snippets = New-Object 'System.Collections.Generic.List[object]'
    $inFence = $false
    $fenceChar = ''
    $fenceLen = 0

    for ($i = 0; $i -lt $Lines.Count; $i++) {
        $line = $Lines[$i]
        $trimmed = $line.TrimStart()
        if ($trimmed -match '^([`~]{3,})(.*)$') {
            $marker = $Matches[1]
            $char = $marker.Substring(0, 1)
            $len = $marker.Length
            if (-not $inFence) {
                $inFence = $true
                $fenceChar = $char
                $fenceLen = $len
                continue
            } elseif ($char -eq $fenceChar -and $len -ge $fenceLen -and [string]::IsNullOrWhiteSpace($Matches[2])) {
                $inFence = $false
                $fenceChar = ''
                $fenceLen = 0
                continue
            }
        }

        if ($inFence) {
            if ($trimmed -and -not $trimmed.StartsWith('#')) {
                $snippets.Add([PSCustomObject]@{
                    LineNumber = $i + 1
                    Text       = $line
                }) | Out-Null
            }
        } else {
            foreach ($m in [regex]::Matches($line, '`([^`\r\n]+)`')) {
                $snippets.Add([PSCustomObject]@{
                    LineNumber = $i + 1
                    Text       = $m.Groups[1].Value
                }) | Out-Null
            }
        }
    }
    return $snippets
}

function Get-LogicalCommandLines {
    param([string[]]$Lines)
    $logical = New-Object 'System.Collections.Generic.List[object]'
    $buffer = ''
    $startLine = 1

    for ($i = 0; $i -lt $Lines.Count; $i++) {
        $line = $Lines[$i]
        if ([string]::IsNullOrEmpty($buffer)) {
            $startLine = $i + 1
            $buffer = $line
        } else {
            $buffer = "$buffer $($line.TrimStart())"
        }

        $trimmedEnd = $line.TrimEnd()
        $continues = $trimmedEnd.EndsWith('\') -or $trimmedEnd.EndsWith('`')
        if ($continues -and ($i + 1) -lt $Lines.Count) {
            $buffer = $buffer.Substring(0, $buffer.Length - 1)
            continue
        }

        $logical.Add([PSCustomObject]@{
            LineNumber = $startLine
            Text       = $buffer
        }) | Out-Null
        $buffer = ''
    }

    if (-not [string]::IsNullOrEmpty($buffer)) {
        $logical.Add([PSCustomObject]@{
            LineNumber = $startLine
            Text       = $buffer
        }) | Out-Null
    }
    return $logical
}

Write-Host '[1/6] Checking required core harness files...' -ForegroundColor Yellow
$requiredFiles = @(
    'AGENTS.md',
    'backend/AGENTS.md',
    'frontend/AGENTS.md',
    'CODING_STANDARDS.md',
    'GLOSSARY.md',
    'DESIGN.md',
    'docs/OPERATIONS.md',
    'docs/PROJECT_STATUS.md',
    '.agents/hooks.json',
    '.agents/scripts/session_start.ps1',
    '.agents/scripts/mem0_helper.ps1',
    '.agents/skills/mem0-memory/SKILL.md'
)
foreach ($relPath in $requiredFiles) {
    if (-not (Test-RepoOrDocPathExists -CandidatePath $relPath -BaseDirs @($repoRoot))) {
        Add-HarnessFailure "Missing required core harness file: $relPath"
    }
}

Write-Host '[2/6] Checking PowerShell syntax of harness scripts...' -ForegroundColor Yellow
$psScripts = New-Object 'System.Collections.Generic.List[string]'
foreach ($dirRel in @('.agents/scripts', 'scripts')) {
    $dirFull = Join-Path $repoRoot ($dirRel -replace '/', [System.IO.Path]::DirectorySeparatorChar)
    if (Test-Path -LiteralPath $dirFull) {
        Get-ChildItem -LiteralPath $dirFull -Recurse -File |
            Where-Object { $_.Extension -eq '.ps1' } |
            ForEach-Object { $psScripts.Add($_.FullName) | Out-Null }
    }
}
foreach ($scriptPath in $psScripts) {
    $tokens = $null
    $parseErrors = $null
    $null = [System.Management.Automation.Language.Parser]::ParseFile($scriptPath, [ref]$tokens, [ref]$parseErrors)
    if ($parseErrors -and $parseErrors.Count -gt 0) {
        $rel = ConvertTo-RepoRelativePath -FullPath $scriptPath
        foreach ($err in $parseErrors) {
            Add-HarnessFailure "PowerShell syntax error in ${rel}:$($err.Extent.StartLineNumber): $($err.Message)"
        }
    }
}

Write-Host '[3/6] Validating .agents/hooks.json...' -ForegroundColor Yellow
$hooksPath = Join-Path $repoRoot ('.agents/hooks.json' -replace '/', [System.IO.Path]::DirectorySeparatorChar)
if (Test-Path -LiteralPath $hooksPath -PathType Leaf) {
    try {
        $hooksJson = Get-Content -LiteralPath $hooksPath -Raw | ConvertFrom-Json
        $harnessConfig = $hooksJson.'gptcraft-harness'
        if ($null -eq $harnessConfig) {
            Add-HarnessFailure '.agents/hooks.json is missing "gptcraft-harness" root object.'
        } else {
            if ($harnessConfig.enabled -ne $true) {
                Add-HarnessFailure '.agents/hooks.json must have gptcraft-harness.enabled = true.'
            }
            $sessionStartHooks = @($harnessConfig.SessionStart)
            if ($sessionStartHooks.Count -eq 0) {
                Add-HarnessFailure '.agents/hooks.json must define at least one SessionStart hook.'
            } else {
                $scriptRefCount = 0
                foreach ($hook in $sessionStartHooks) {
                    $cmd = [string]$hook.command
                    if ([string]::IsNullOrWhiteSpace($cmd)) {
                        Add-HarnessFailure '.agents/hooks.json SessionStart hook has an empty command.'
                        continue
                    }

                    $foundPaths = New-Object 'System.Collections.Generic.List[string]'

                    # Match Join-Path $root '.agents/scripts/session_start.ps1' or Join-Path (git ...) '...'
                    foreach ($m in [regex]::Matches($cmd, 'Join-Path\s+(?:\([^)]+\)|\$\w+)\s+((?:[''"][^''"]+[''"]\s*)+)')) {
                        $argTokens = [regex]::Matches($m.Groups[1].Value, '[''"]([^''"]+)[''"]') |
                            ForEach-Object { $_.Groups[1].Value }
                        if ($argTokens.Count -gt 0) {
                            $foundPaths.Add(($argTokens -join '/')) | Out-Null
                        }
                    }

                    # Match direct .agents/... or scripts/... script path references
                    foreach ($m in [regex]::Matches($cmd, '(?<![A-Za-z0-9_.-])(?:\.[\\/])?((?:\.agents|scripts)[\\/][^\s''"`]+?\.(?:ps1|py|sh|cmd|bat))')) {
                        $foundPaths.Add($m.Groups[1].Value) | Out-Null
                    }

                    if ($foundPaths.Count -eq 0) {
                        Add-HarnessFailure ".agents/hooks.json SessionStart command does not reference a verifiable repo script: $cmd"
                    } else {
                        foreach ($refPath in ($foundPaths | Select-Object -Unique)) {
                            $scriptRefCount++
                            if (-not (Test-RepoOrDocPathExists -CandidatePath $refPath -BaseDirs @($repoRoot))) {
                                Add-HarnessFailure ".agents/hooks.json references missing script: $refPath"
                            }
                        }
                    }
                }
                if ($scriptRefCount -eq 0) {
                    Add-HarnessFailure '.agents/hooks.json did not resolve any SessionStart script paths.'
                }
            }
        }
    } catch {
        Add-HarnessFailure "Failed to parse .agents/hooks.json: $($_.Exception.Message)"
    }
}

Write-Host '[4/6] Cross-checking mem0-memory/SKILL.md actions against mem0_helper.ps1...' -ForegroundColor Yellow
$mem0HelperPath = Join-Path $repoRoot ('.agents/scripts/mem0_helper.ps1' -replace '/', [System.IO.Path]::DirectorySeparatorChar)
$mem0SkillPath = Join-Path $repoRoot ('.agents/skills/mem0-memory/SKILL.md' -replace '/', [System.IO.Path]::DirectorySeparatorChar)
if ((Test-Path -LiteralPath $mem0HelperPath -PathType Leaf) -and (Test-Path -LiteralPath $mem0SkillPath -PathType Leaf)) {
    $tokens = $null
    $parseErrors = $null
    $helperAst = [System.Management.Automation.Language.Parser]::ParseFile($mem0HelperPath, [ref]$tokens, [ref]$parseErrors)
    $actionParam = $helperAst.Find({
        param($node)
        $node -is [System.Management.Automation.Language.ParameterAst] -and
        $node.Name.VariablePath.UserPath -eq 'Action'
    }, $true)

    $allowedActions = New-Object 'System.Collections.Generic.HashSet[string]' ([System.StringComparer]::OrdinalIgnoreCase)
    if ($null -ne $actionParam) {
        $validateSetAttr = $actionParam.Attributes | Where-Object {
            $_ -is [System.Management.Automation.Language.AttributeAst] -and $_.TypeName.Name -eq 'ValidateSet'
        } | Select-Object -First 1
        if ($null -ne $validateSetAttr) {
            foreach ($arg in $validateSetAttr.PositionalArguments) {
                $val = [string]$arg.SafeGetValue()
                if (-not [string]::IsNullOrWhiteSpace($val)) {
                    $allowedActions.Add($val) | Out-Null
                }
            }
        }
    }

    if ($allowedActions.Count -eq 0) {
        Add-HarnessFailure 'Could not extract [ValidateSet(...)] actions for $Action from .agents/scripts/mem0_helper.ps1.'
    } else {
        $skillLines = Get-Content -LiteralPath $mem0SkillPath
        $skillRaw = $skillLines -join "`n"

        # 1. Check explicit -Action <name> invocations anywhere in SKILL.md
        foreach ($m in [regex]::Matches($skillRaw, '(?i)(?<![A-Za-z0-9_-])-Action\s+[''"]?([A-Za-z][A-Za-z0-9_-]*)[''"]?')) {
            $act = $m.Groups[1].Value
            if (-not $allowedActions.Contains($act)) {
                Add-HarnessFailure ".agents/skills/mem0-memory/SKILL.md documents unsupported mem0_helper.ps1 -Action '$act' (allowed: $($allowedActions -join ', '))."
            }
        }

        # 2. Check positional mem0_helper.ps1 <action> invocations
        foreach ($m in [regex]::Matches($skillRaw, '(?i)mem0_helper\.ps1[''"]?\s+([A-Za-z][A-Za-z0-9_-]*)')) {
            $act = $m.Groups[1].Value
            if (-not $allowedActions.Contains($act)) {
                Add-HarnessFailure ".agents/skills/mem0-memory/SKILL.md documents unsupported positional mem0_helper.ps1 action '$act' (allowed: $($allowedActions -join ', '))."
            }
        }

        # 3. Check mem0 CLI subcommands in code blocks and inline backticks
        foreach ($snippet in (Get-MarkdownCodeSnippets -Lines $skillLines)) {
            foreach ($m in [regex]::Matches($snippet.Text, '(?-i)(?:^|[;&|]\s*|\s)mem0(?:\s+--json)*\s+([a-z][a-z0-9_-]*)\b')) {
                $subcmd = $m.Groups[1].Value
                if (-not $allowedActions.Contains($subcmd)) {
                    Add-HarnessFailure ".agents/skills/mem0-memory/SKILL.md:$($snippet.LineNumber) documents unsupported mem0 CLI action '$subcmd' (allowed: $($allowedActions -join ', '))."
                }
            }
        }
    }
}

Write-Host '[5/6] Validating local markdown links and repo path references...' -ForegroundColor Yellow
$docFilesToCheck = New-Object 'System.Collections.Generic.List[string]'
foreach ($relDoc in @(
    'AGENTS.md',
    'backend/AGENTS.md',
    'frontend/AGENTS.md',
    'CODING_STANDARDS.md',
    'README.md',
    'docs/OPERATIONS.md',
    'docs/PROJECT_STATUS.md'
)) {
    $fullDoc = Join-Path $repoRoot ($relDoc -replace '/', [System.IO.Path]::DirectorySeparatorChar)
    if (Test-Path -LiteralPath $fullDoc -PathType Leaf) {
        $docFilesToCheck.Add($fullDoc) | Out-Null
    }
}
$skillsDir = Join-Path $repoRoot ('.agents/skills' -replace '/', [System.IO.Path]::DirectorySeparatorChar)
if (Test-Path -LiteralPath $skillsDir) {
    Get-ChildItem -LiteralPath $skillsDir -Directory | ForEach-Object {
        $skillMd = Join-Path $_.FullName 'SKILL.md'
        if (Test-Path -LiteralPath $skillMd -PathType Leaf) {
            $docFilesToCheck.Add($skillMd) | Out-Null
        }
    }
}

$rootHarnessFiles = @('AGENTS.md', 'CODING_STANDARDS.md', 'GLOSSARY.md', 'DESIGN.md', 'README.md', 'vercel.json')
$backendLockFiles = @('requirements.in', 'requirements.lock', 'requirements-dev.lock')

foreach ($docFull in $docFilesToCheck) {
    $docRel = ConvertTo-RepoRelativePath -FullPath $docFull
    $docDir = Split-Path -Parent $docFull
    $lines = Get-Content -LiteralPath $docFull
    $proseLines = Get-NonCodeMarkdownLines -Lines $lines

    foreach ($entry in $proseLines) {
        $lineNo = $entry.LineNumber
        $lineText = $entry.Text

        # 1. Markdown links [text](target)
        foreach ($m in [regex]::Matches($lineText, '(?<!!)\[[^\]]+\]\(([^)\r\n]+)\)')) {
            $rawTarget = $m.Groups[1].Value.Trim()
            if ($rawTarget.StartsWith('<') -and $rawTarget.EndsWith('>')) {
                $rawTarget = $rawTarget.Substring(1, $rawTarget.Length - 2).Trim()
            } else {
                $rawTarget = ($rawTarget -split '\s+')[0]
            }
            if ([string]::IsNullOrWhiteSpace($rawTarget)) { continue }
            if ($rawTarget -match '^(?i)(https?|mailto|file|conversation|tel|data):' -or $rawTarget.StartsWith('//')) { continue }
            if ($rawTarget.StartsWith('#')) { continue }

            $cleanTarget = ($rawTarget -split '[#?]')[0]
            if ([string]::IsNullOrWhiteSpace($cleanTarget)) { continue }
            if ($cleanTarget -match '[*?<>\{\}$]') { continue }

            $cleanTarget = Remove-LeadingDotSlash -Value $cleanTarget
            if ($cleanTarget.StartsWith('/')) { continue }

            if (-not (Test-RepoOrDocPathExists -CandidatePath $cleanTarget -BaseDirs @($docDir, $repoRoot))) {
                Add-HarnessFailure "Broken markdown link in ${docRel}:${lineNo} -> '$rawTarget'"
            }
        }

        # 2. Inline backticked concrete repo-relative paths
        foreach ($m in [regex]::Matches($lineText, '`([^`\r\n]+)`')) {
            $span = $m.Groups[1].Value
            foreach ($rawToken in (Split-CommandTokens -Text $span)) {
                $tok = $rawToken.Trim().Trim('''', '"').TrimEnd('.', ',', ';', ':', ')', ']')
                if ([string]::IsNullOrWhiteSpace($tok)) { continue }
                if ($tok -match '://|@' -or $tok.StartsWith('/') -or $tok.StartsWith('~/') -or $tok.StartsWith('-')) { continue }
                if ($tok -match '[*?<>\{\}$\[\]&|=]' -or $tok.Contains('...')) { continue }

                $norm = Remove-LeadingDotSlash -Value $tok
                if ([string]::IsNullOrWhiteSpace($norm)) { continue }

                # Skip ephemeral local environment/build paths that may not exist on a fresh checkout
                if ($norm -match '(^|/)\.venv(/|$)|(^|/)node_modules(/|$)|(^|/)dist(/|$)|(^|/)\.git(/|$)|(^|/)\.pytest_cache(/|$)|(^|/)\.env(\.local)?$|\.pyc$') {
                    continue
                }

                $cleanNoAnchor = ($norm -split '[#?]')[0]
                if ([string]::IsNullOrWhiteSpace($cleanNoAnchor)) { continue }

                if ($cleanNoAnchor -match '^(backend|frontend|docs|scripts|\.agents|\.github|api)/') {
                    if (-not (Test-RepoOrDocPathExists -CandidatePath $cleanNoAnchor -BaseDirs @($repoRoot))) {
                        Add-HarnessFailure "Missing repo path referenced in ${docRel}:${lineNo} -> '$rawToken'"
                    }
                } elseif ($cleanNoAnchor -match '^app/' -and ($docRel -eq 'backend/AGENTS.md' -or $docRel -eq 'CODING_STANDARDS.md' -or $docRel -like '.agents/skills/gptcraft-*/SKILL.md')) {
                    if (-not (Test-RepoOrDocPathExists -CandidatePath $cleanNoAnchor -BaseDirs @((Join-Path $repoRoot 'backend')))) {
                        Add-HarnessFailure "Missing backend path referenced in ${docRel}:${lineNo} -> '$rawToken'"
                    }
                } elseif ($cleanNoAnchor -match '^src/' -and ($docRel -eq 'frontend/AGENTS.md' -or $docRel -eq 'CODING_STANDARDS.md' -or $docRel -like '.agents/skills/gptcraft-*/SKILL.md')) {
                    if (-not (Test-RepoOrDocPathExists -CandidatePath $cleanNoAnchor -BaseDirs @((Join-Path $repoRoot 'frontend')))) {
                        Add-HarnessFailure "Missing frontend path referenced in ${docRel}:${lineNo} -> '$rawToken'"
                    }
                } elseif ($span.Trim() -eq $rawToken -and $rootHarnessFiles -contains $cleanNoAnchor) {
                    if (-not (Test-RepoOrDocPathExists -CandidatePath $cleanNoAnchor -BaseDirs @($repoRoot))) {
                        Add-HarnessFailure "Missing root harness file referenced in ${docRel}:${lineNo} -> '$rawToken'"
                    }
                } elseif ($span.Trim() -eq $rawToken -and $backendLockFiles -contains $cleanNoAnchor -and ($docRel -eq 'backend/AGENTS.md' -or $docRel -eq 'docs/OPERATIONS.md')) {
                    if (-not (Test-RepoOrDocPathExists -CandidatePath $cleanNoAnchor -BaseDirs @((Join-Path $repoRoot 'backend')))) {
                        Add-HarnessFailure "Missing backend lock/requirement file referenced in ${docRel}:${lineNo} -> '$rawToken'"
                    }
                }
            }
        }
    }
}

Write-Host '[6/6] Scanning harness/docs/skills for banned drifted patterns...' -ForegroundColor Yellow
$scanFiles = New-Object 'System.Collections.Generic.List[string]'
foreach ($relFile in @(
    'AGENTS.md',
    'backend/AGENTS.md',
    'frontend/AGENTS.md',
    'CODING_STANDARDS.md',
    'GLOSSARY.md',
    'DESIGN.md',
    'README.md',
    '.agents/hooks.json'
)) {
    $full = Join-Path $repoRoot ($relFile -replace '/', [System.IO.Path]::DirectorySeparatorChar)
    if (Test-Path -LiteralPath $full -PathType Leaf) {
        $scanFiles.Add($full) | Out-Null
    }
}

$docsDir = Join-Path $repoRoot 'docs'
if (Test-Path -LiteralPath $docsDir) {
    Get-ChildItem -LiteralPath $docsDir -Recurse -File |
        Where-Object { $_.Extension -eq '.md' } |
        ForEach-Object { $scanFiles.Add($_.FullName) | Out-Null }
}

$agentsDir = Join-Path $repoRoot '.agents'
if (Test-Path -LiteralPath $agentsDir) {
    Get-ChildItem -LiteralPath $agentsDir -Recurse -File |
        Where-Object { $_.Extension -in @('.md', '.ps1') } |
        ForEach-Object { $scanFiles.Add($_.FullName) | Out-Null }
}

$negationPattern = '(?i)\b(?:do not|don''t|never|avoid|deprecated|obsolete|historical|instead of)\b'

foreach ($scanPath in ($scanFiles | Select-Object -Unique)) {
    $rel = ConvertTo-RepoRelativePath -FullPath $scanPath
    $lines = Get-Content -LiteralPath $scanPath
    $logicalLines = Get-LogicalCommandLines -Lines $lines

    foreach ($l in $logicalLines) {
        $lineNo = $l.LineNumber
        $text = $l.Text

        if ($text -match '(?i)\bpip\s+install\b[^\r\n]*?(?:-r|--requirement)\s+(?:[^\s"'']*[/\\])?requirements\.txt\b') {
            if ($text -notmatch $negationPattern) {
                Add-HarnessFailure "Banned drifted command in ${rel}:${lineNo}: unhashed 'pip install -r requirements.txt' (use hashed requirements-dev.lock)."
            }
        }

        if ($text -match '(?i)\bpip\s+install\b[^\r\n]*\brequirements-dev\.lock\b' -and $text -notmatch '(?i)--require-hashes') {
            Add-HarnessFailure "Banned drifted command in ${rel}:${lineNo}: 'requirements-dev.lock' used with pip install without '--require-hashes'."
        }
    }

    for ($i = 0; $i -lt $lines.Count; $i++) {
        $lineNo = $i + 1
        $line = $lines[$i]

        if ($line -match '(?i)/users/me/(?:preferences|memories)\b') {
            Add-HarnessFailure "Banned drifted route in ${rel}:${lineNo}: '$($Matches[0])' (actual routes are under /memory)."
        }

        if ($line -match '(?i)\bnit2314\b') {
            Add-HarnessFailure "Banned personal identifier in ${rel}:${lineNo}: 'nit2314'."
        }

        if ($line -match '(?i)(?<![A-Za-z0-9._-])/(?:wayfinder|triage|code-review)(?![A-Za-z0-9._-])') {
            Add-HarnessFailure "Banned drifted slash command in ${rel}:${lineNo}: '$($Matches[0])'."
        }

        if ($rel -eq '.agents/skills/mem0-memory/SKILL.md' -and $line -match '(?i)(?:\bmem0\s+update\b|-Action\s+[''"]?update\b|\bAction\s+update\b)') {
            Add-HarnessFailure "Banned unsupported mem0 update action in ${rel}:${lineNo}: '$($Matches[0])'."
        }
    }
}

if ($failures.Count -gt 0) {
    Write-Host "`n[FAIL] Harness drift check found $($failures.Count) issue(s):" -ForegroundColor Red
    foreach ($f in $failures) {
        Write-Host "  - $f" -ForegroundColor Red
    }
    throw "Harness drift check failed with $($failures.Count) issue(s)."
}

$global:LASTEXITCODE = 0
Write-Host '[PASS] Harness drift checks passed with zero issues.' -ForegroundColor Green
