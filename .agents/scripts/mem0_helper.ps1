<#
.SYNOPSIS
Developer-only Mem0 preference memory helper for the GPTCraft Personal Agent harness.

.DESCRIPTION
Provides explicit, on-demand access to developer Mem0 memories scoped by MEM0_USER_ID
(or -UserId). This helper is strictly for developer preferences and never serves as
runtime application memory or architecture ground truth.
#>
[CmdletBinding()]
param (
    [Parameter(Position = 0, Mandatory = $true)]
    [ValidateSet("status", "list", "search", "add", "get", "delete", "help")]
    [string]$Action,

    [Parameter(Position = 1)]
    [string]$QueryOrText,

    [Parameter()]
    [string]$Id,

    [Parameter()]
    [string]$UserId = $env:MEM0_USER_ID,

    [Parameter()]
    [switch]$Json
)

$ErrorActionPreference = "Stop"

$userScopedActions = @("list", "search", "add")
if ($Action -in $userScopedActions -and [string]::IsNullOrWhiteSpace($UserId)) {
    Write-Error "Mem0 user scope is required for '$Action'. Set `$env:MEM0_USER_ID or pass -UserId '<user-id>'."
}

if ($Action -ne "help" -and -not (Get-Command mem0 -ErrorAction SilentlyContinue)) {
    Write-Error "mem0 CLI is not installed or not on PATH. Install @mem0/cli to use developer preference memory."
}

switch ($Action) {
    "status" {
        if ($Json) {
            mem0 --json status
        } else {
            mem0 status
        }
    }
    "list" {
        if ($Json) {
            mem0 --json list --user-id $UserId
        } else {
            mem0 list --user-id $UserId
        }
    }
    "search" {
        if ([string]::IsNullOrWhiteSpace($QueryOrText)) {
            Write-Error "Please specify a search query: pwsh -File .agents/scripts/mem0_helper.ps1 -Action search -QueryOrText 'query'"
        }
        if ($Json) {
            mem0 --json search $QueryOrText --user-id $UserId
        } else {
            mem0 search $QueryOrText --user-id $UserId
        }
    }
    "add" {
        if ([string]::IsNullOrWhiteSpace($QueryOrText)) {
            Write-Error "Please specify text to remember: pwsh -File .agents/scripts/mem0_helper.ps1 -Action add -QueryOrText 'text'"
        }
        if ($Json) {
            mem0 --json add $QueryOrText --user-id $UserId
        } else {
            mem0 add $QueryOrText --user-id $UserId
        }
    }
    "get" {
        if ([string]::IsNullOrWhiteSpace($Id)) {
            Write-Error "Please specify memory Id: pwsh -File .agents/scripts/mem0_helper.ps1 -Action get -Id '<id>'"
        }
        if ($Json) {
            mem0 --json get $Id
        } else {
            mem0 get $Id
        }
    }
    "delete" {
        if ([string]::IsNullOrWhiteSpace($Id)) {
            Write-Error "Please specify memory Id: pwsh -File .agents/scripts/mem0_helper.ps1 -Action delete -Id '<id>'"
        }
        if ($Json) {
            mem0 --json delete $Id --force
        } else {
            mem0 delete $Id --force
        }
    }
    "help" {
        Write-Output "GPTCraft Personal Agent - developer-only Mem0 helper"
        Write-Output "Actions: status, list, search, add, get, delete, help"
        Write-Output "User scope (required for list, search, add): `$env:MEM0_USER_ID or -UserId '<user-id>'"
        if (Get-Command mem0 -ErrorAction SilentlyContinue) {
            mem0 --help
        }
    }
}

if ($Action -ne "help" -and $LASTEXITCODE) {
    exit $LASTEXITCODE
}
