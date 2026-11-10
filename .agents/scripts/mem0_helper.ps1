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
    [string]$UserId = "nit2314",

    [Parameter()]
    [switch]$Json
)

$ErrorActionPreference = "Stop"

switch ($Action) {
    "status" {
        mem0 status
    }
    "list" {
        if ($Json) {
            mem0 --json list --user-id $UserId
        } else {
            mem0 list --user-id $UserId
        }
    }
    "search" {
        if (-not $QueryOrText) {
            Write-Error "Please specify search query: .\mem0_helper.ps1 -Action search -QueryOrText 'query'"
        }
        if ($Json) {
            mem0 --json search $QueryOrText --user-id $UserId
        } else {
            mem0 search $QueryOrText --user-id $UserId
        }
    }
    "add" {
        if (-not $QueryOrText) {
            Write-Error "Please specify text to remember: .\mem0_helper.ps1 -Action add -QueryOrText 'text'"
        }
        if ($Json) {
            mem0 --json add $QueryOrText --user-id $UserId
        } else {
            mem0 add $QueryOrText --user-id $UserId
        }
    }
    "get" {
        if (-not $Id) {
            Write-Error "Please specify memory Id: .\mem0_helper.ps1 -Action get -Id '<id>'"
        }
        mem0 get $Id
    }
    "delete" {
        if (-not $Id) {
            Write-Error "Please specify memory Id: .\mem0_helper.ps1 -Action delete -Id '<id>'"
        }
        mem0 delete $Id --yes
    }
    Default {
        mem0 --help
    }
}
