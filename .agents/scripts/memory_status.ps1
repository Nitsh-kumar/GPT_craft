function ConvertTo-ProjectMemoryStatus {
    param([string]$Raw, [int]$ExitCode)
    if ($ExitCode -ne 0) { return 'lookup failed (continuing without memory)' }
    try {
        $parsed = $Raw | ConvertFrom-Json -ErrorAction Stop
        if ($parsed.status -ne 'success') { return 'lookup failed (continuing without memory)' }
        $entries = if ($parsed.data.results) { $parsed.data.results } else { $parsed.data }
        $count = @($entries | Where-Object { $_.memory -match '\bGPTCraft\b' }).Count
        # Status only: untrusted memory text may contain credentials. Retrieve
        # selected project facts deliberately through the helper, never stdout.
        return "retrieved $count project facts (load deliberately with the memory helper)"
    } catch { return 'lookup failed (continuing without memory)' }
}
