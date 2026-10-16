# Self-updater for the Claude Code enterprise agent kit (Windows).
# Runs from a SessionStart hook in the background. At most once per interval it
# fetches release tags and, if a newer released version exists, re-runs the
# installer from that tag. It never blocks or fails a session: errors are logged.
#
# Opt out:  $env:CLAUDE_AGENTS_AUTO_UPDATE = '0'  (or create the file
#           __CLAUDE_HOME__/enterprise-agents/auto-update-disabled)
# Options:  CLAUDE_AGENTS_UPDATE_INTERVAL_HOURS (default 24)
#           CLAUDE_AGENTS_REQUIRE_SIGNED_TAGS=1 (only install signed tags)
$ErrorActionPreference = 'Continue'
$claudeHome = '__CLAUDE_HOME__'
$state = Join-Path $claudeHome 'enterprise-agents'
$src   = Join-Path $state 'src'
$log   = Join-Path $state 'update.log'
$lock  = Join-Path $state 'update.lock'
$haveLock = $false

function Log([string]$m) {
    try { Add-Content -Path $log -Value ("{0} {1}" -f (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ'), $m) } catch { }
}

try {
    if ($env:CLAUDE_AGENTS_AUTO_UPDATE -eq '0') { exit 0 }
    if (Test-Path (Join-Path $state 'auto-update-disabled')) { exit 0 }
    if (-not (Test-Path (Join-Path $src '.git'))) { exit 0 }
    if (-not (Get-Command git -ErrorAction SilentlyContinue)) { exit 0 }

    $interval = 24
    if ($env:CLAUDE_AGENTS_UPDATE_INTERVAL_HOURS -match '^\d+$') { $interval = [int]$env:CLAUDE_AGENTS_UPDATE_INTERVAL_HOURS }
    $now = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
    $last = 0
    $stampFile = Join-Path $state 'last-check'
    if (Test-Path $stampFile) { [long]::TryParse(("" + (Get-Content $stampFile -Raw)).Trim(), [ref]$last) | Out-Null }
    if (($now - $last) -lt ($interval * 3600)) { exit 0 }

    if (Test-Path $lock) {
        if (((Get-Date) - (Get-Item $lock).LastWriteTime).TotalHours -gt 1) { Remove-Item $lock -Force }
        exit 0
    }
    New-Item -ItemType Directory $lock -ErrorAction Stop | Out-Null
    $haveLock = $true
    Set-Content -Path $stampFile -Value $now

    if ((Test-Path $log) -and (Get-Item $log).Length -gt 200000) {
        (Get-Content $log -Tail 200) | Set-Content $log
    }

    $env:GIT_TERMINAL_PROMPT = '0'
    $g = @('-C', $src, '-c', 'http.lowSpeedLimit=1000', '-c', 'http.lowSpeedTime=30')
    # Branch first, then tags without '+': a tag moved upstream is refused, the rest still arrive.
    & git @g fetch --quiet --no-tags origin '+refs/heads/main:refs/remotes/origin/main' 2>$null
    if ($LASTEXITCODE -ne 0) { Log 'fetch failed (offline or repo unreachable); will retry next interval'; exit 0 }
    & git @g fetch --quiet --no-tags origin 'refs/tags/v*:refs/tags/v*' 2>$null
    if ($LASTEXITCODE -ne 0) { Log 'warning: some release tags were rejected (moved upstream?); using the tags that verify' }

    $installed = '0.0.0'
    if (Test-Path (Join-Path $state 'VERSION')) { $installed = ("" + (Get-Content (Join-Path $state 'VERSION') -Raw)).Trim() }
    $latest = $null; $target = $null
    foreach ($tag in @(& git @g tag -l 'v[0-9]*' --sort=-v:refname)) {
        $v = $tag.TrimStart('v')
        try { if ([version]$v -le [version]$installed) { break } } catch { continue }
        & git @g merge-base --is-ancestor "$tag^{commit}" origin/main 2>$null
        if ($LASTEXITCODE -ne 0) { Log "tag $tag is not on origin/main; skipping"; continue }
        if (("" + (& git @g show "${tag}:VERSION" 2>$null)).Trim() -ne $v) { Log "tag $tag does not contain VERSION $v; skipping"; continue }
        if ($env:CLAUDE_AGENTS_REQUIRE_SIGNED_TAGS -eq '1') {
            & git @g verify-tag $tag 2>$null
            if ($LASTEXITCODE -ne 0) { Log "tag $tag has no valid signature; skipping"; continue }
        }
        $latest = $tag; $target = $v; break
    }
    if (-not $latest) { exit 0 }

    & git @g -c advice.detachedHead=false checkout --quiet --force $latest 2>$null
    if ($LASTEXITCODE -ne 0) { Log "checkout of $latest failed"; exit 0 }

    $out = & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $src 'install.ps1') -ClaudeHome $claudeHome -Quiet -SelfUpdate 2>&1
    if ($LASTEXITCODE -eq 0) { Log "updated $installed -> $target (takes effect in the next Claude Code session)" }
    else { Log "installer for $latest failed; previous version left in place: $out" }
}
catch { Log "self-update error: $($_.Exception.Message)" }
finally { if ($haveLock -and (Test-Path $lock)) { Remove-Item $lock -Force -ErrorAction SilentlyContinue } }
exit 0
