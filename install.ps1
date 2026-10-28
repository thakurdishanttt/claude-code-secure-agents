# Installs the Claude Code enterprise agent team globally (all projects) on Windows.
# Usage:  powershell -ExecutionPolicy Bypass -File .\install.ps1 [-NoAutoUpdate] [-Quiet]
# Env:    CLAUDE_AGENTS_REPO  git URL the self-updater pulls releases from (default: this
#                             checkout's origin, else the public repo; use your internal mirror)
param(
    [string]$ClaudeHome = (Join-Path $env:USERPROFILE '.claude'),
    [switch]$NoAutoUpdate,
    [switch]$Quiet,
    [switch]$SelfUpdate,
    [switch]$AllowDowngrade
)
$ErrorActionPreference = 'Stop'

$src            = Split-Path -Parent $MyInvocation.MyCommand.Path
$fwd            = $ClaudeHome -replace '\\', '/'
$stamp          = Get-Date -Format 'yyyyMMdd-HHmmss'
$utf8           = New-Object System.Text.UTF8Encoding $false
$reminderMarker = 'prompt-reminder.txt'
$updateMarker   = 'self-update'
$state          = Join-Path $ClaudeHome 'enterprise-agents'
$defaultRepo    = 'https://github.com/thakurdishanttt/claude-code-secure-agents.git'
$keepBackups    = 5

$autoUpdate = -not $NoAutoUpdate
if ($env:CLAUDE_AGENTS_AUTO_UPDATE -eq '0') { $autoUpdate = $false }
if ($SelfUpdate -and (Test-Path (Join-Path $state 'auto-update-disabled'))) { $autoUpdate = $false }

function Say([string]$m) { if (-not $Quiet) { Write-Host $m } }
function Write-Utf8([string]$path, [string]$text) {
    # Write to a temp file and rename, so a running script (the self-updater) is never truncated.
    $tmp = "$path.new-$PID"
    [System.IO.File]::WriteAllText($tmp, $text, $utf8)
    Move-Item -Force $tmp $path
}
function Read-Utf8([string]$path) { [System.IO.File]::ReadAllText($path, $utf8) }
function Backup-IfChanged([string]$path, [string]$newText) {
    if (-not (Test-Path $path)) { return }
    if ((Read-Utf8 $path) -ceq $newText) { return }
    Copy-Item $path "$path.bak-$stamp"
    Say "  backup: $path.bak-$stamp"
    Get-ChildItem -Path "$path.bak-*" -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending | Select-Object -Skip $keepBackups |
        Remove-Item -Force -ErrorAction SilentlyContinue
}
function Set-IfChanged([string]$path, [string]$text, [string]$label) {
    if ((Test-Path $path) -and ((Read-Utf8 $path) -ceq $text)) { return }
    Backup-IfChanged $path $text
    Write-Utf8 $path $text
    Say "  installed: $label"
}

# Never replace a newer installed kit with an older checkout (e.g. a stale clone).
$newVersion = ("" + [System.IO.File]::ReadAllText((Join-Path $src 'VERSION'))).Trim()
$oldVersion = ''
if (Test-Path (Join-Path $state 'VERSION')) { $oldVersion = ("" + [System.IO.File]::ReadAllText((Join-Path $state 'VERSION'))).Trim() }
if ($oldVersion -and -not $AllowDowngrade) {
    try {
        if ([version]$oldVersion -gt [version]$newVersion) {
            Write-Host "Already on a newer version ($oldVersion) than this checkout ($newVersion); nothing changed."
            Write-Host "Update this checkout (git pull) or pass -AllowDowngrade to install it anyway."
            exit 0
        }
    } catch { }
}
if (-not $oldVersion -and (Test-Path (Join-Path $ClaudeHome 'agents/planner.md'))) { $oldVersion = '1.0.x (pre-auto-update)' }
if (-not $oldVersion) { Say "Installing $newVersion into $ClaudeHome" }
elseif ($oldVersion -eq $newVersion) { Say "Reinstalling $newVersion into $ClaudeHome (already up to date; repairing)" }
else { Say "Upgrading $oldVersion -> $newVersion in $ClaudeHome" }
foreach ($d in 'agents', 'commands', 'standards', 'hooks', 'enterprise-agents') {
    New-Item -ItemType Directory -Force (Join-Path $ClaudeHome $d) | Out-Null
}

# 0. Stage (render) everything first so a failure never leaves a half-installed kit.
$staged = [ordered]@{}
$globs = @('agents/*.md', 'commands/*.md', 'standards/*.md', 'hooks/prompt-reminder.txt', 'hooks/self-update.ps1')
foreach ($g in $globs) {
    foreach ($item in (Get-ChildItem -Path (Join-Path $src $g) -File -ErrorAction SilentlyContinue | Sort-Object Name)) {
        if ($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) { Write-Warning "skipping link $($item.Name)"; continue }
        $rel = ($g.Split('/')[0]) + '/' + $item.Name
        $staged[$rel] = (Read-Utf8 $item.FullName).Replace('__CLAUDE_HOME__', $fwd)
    }
}
$block = (Read-Utf8 (Join-Path $src 'CLAUDE.global.md')).Replace('__CLAUDE_HOME__', $fwd).Trim()

# 1. Agents, commands, standards, hook scripts
foreach ($rel in $staged.Keys) {
    Set-IfChanged (Join-Path $ClaudeHome $rel) $staged[$rel] $rel
}

# Files a previous version installed but this one dropped: set aside, never silently delete.
$manifest = Join-Path $state 'manifest.txt'
if (Test-Path $manifest) {
    foreach ($old in (Get-Content $manifest)) {
        if ($old -and -not $staged.Contains($old)) {
            $p = Join-Path $ClaudeHome $old
            if (Test-Path $p) { Move-Item $p "$p.removed-$stamp"; Say "  retired: $old" }
        }
    }
}
Write-Utf8 $manifest (($staged.Keys -join "`n") + "`n")

# 2. Global CLAUDE.md: replace our marked block, or append it; never drop user content
$claudeMd = Join-Path $ClaudeHome 'CLAUDE.md'
if (Test-Path $claudeMd) {
    $existing = Read-Utf8 $claudeMd
    $pattern = '(?s)<!-- BEGIN claude-enterprise-agents -->.*?<!-- END claude-enterprise-agents -->'
    if ($existing -match $pattern) {
        $new = [regex]::Replace($existing, $pattern, { param($m) $block })
    } else {
        $new = $existing.TrimEnd() + "`r`n`r`n" + $block + "`r`n"
    }
    Set-IfChanged $claudeMd $new 'CLAUDE.md'
} else {
    Write-Utf8 $claudeMd ($block + "`r`n")
    Say "  created: CLAUDE.md"
}

# 3. settings.json: UserPromptSubmit (rules) and SessionStart (self-update) hooks
$settingsPath = Join-Path $ClaudeHome 'settings.json'
$raw = ''
if (Test-Path $settingsPath) { $raw = Read-Utf8 $settingsPath }
if ($raw.Trim()) { $settings = $raw | ConvertFrom-Json } else { $settings = New-Object PSObject }
if (-not ($settings.PSObject.Properties.Name -contains 'hooks')) {
    $settings | Add-Member -NotePropertyName hooks -NotePropertyValue (New-Object PSObject)
}
function Get-Event([string]$name) {
    if ($settings.hooks.PSObject.Properties.Name -contains $name) { return @($settings.hooks.$name) }
    return @()
}
function Set-Event([string]$name, $value) {
    if ($settings.hooks.PSObject.Properties.Name -contains $name) { $settings.hooks.$name = @($value) }
    else { $settings.hooks | Add-Member -NotePropertyName $name -NotePropertyValue @($value) }
}
function Test-Marker($entries, [string]$marker) {
    foreach ($e in $entries) { foreach ($h in @($e.hooks)) { if ("$($h.command)" -like "*$marker*") { return $true } } }
    return $false
}

$ups = Get-Event 'UserPromptSubmit'
if (-not (Test-Marker $ups $reminderMarker)) {
    $ups += [pscustomobject]@{ hooks = @([pscustomobject]@{
        type = 'command'; command = "cat `"$fwd/hooks/$reminderMarker`""; timeout = 10 }) }
    Set-Event 'UserPromptSubmit' $ups
    Say "  added rules hook (UserPromptSubmit)"
}
$ss = Get-Event 'SessionStart'
if ($autoUpdate -and -not (Test-Marker $ss $updateMarker)) {
    $ss += [pscustomobject]@{ matcher = 'startup'; hooks = @([pscustomobject]@{
        type = 'command'
        command = "powershell -NoProfile -ExecutionPolicy Bypass -File `"$fwd/hooks/self-update.ps1`""
        async = $true; timeout = 120 }) }
    Set-Event 'SessionStart' $ss
    Say "  added self-update hook (SessionStart)"
}
if (-not $autoUpdate -and (Test-Marker $ss $updateMarker)) {
    $kept = @($ss | Where-Object { -not (Test-Marker @($_) $updateMarker) })
    if ($kept.Count) { Set-Event 'SessionStart' $kept } else { $settings.hooks.PSObject.Properties.Remove('SessionStart') }
    Say "  removed self-update hook (auto-update disabled)"
}
# Read-only access to the standard, so agents can read it without a permission prompt.
$homeFwd = $env:USERPROFILE -replace '\\', '/'
if ($homeFwd -and $fwd.StartsWith("$homeFwd/", [StringComparison]::OrdinalIgnoreCase)) {
    $readRule = "Read(~/$($fwd.Substring($homeFwd.Length + 1))/standards/**)"
    if (-not ($settings.PSObject.Properties.Name -contains 'permissions')) {
        $settings | Add-Member -NotePropertyName permissions -NotePropertyValue (New-Object PSObject)
    }
    $allow = @()
    if ($settings.permissions.PSObject.Properties.Name -contains 'allow') { $allow = @($settings.permissions.allow) }
    if ($allow -notcontains $readRule) {
        $allow += $readRule
        if ($settings.permissions.PSObject.Properties.Name -contains 'allow') { $settings.permissions.allow = $allow }
        else { $settings.permissions | Add-Member -NotePropertyName allow -NotePropertyValue $allow }
        Say "  allowed reading the standard without prompts"
    }
}
# Windows PowerShell 5.1 adds a Count/value wrapper to arrays in JSON unless this type data is removed.
Remove-TypeData -TypeName System.Array -ErrorAction SilentlyContinue
$json = $settings | ConvertTo-Json -Depth 50
$null = $json | ConvertFrom-Json   # validate before writing
Set-IfChanged $settingsPath $json 'settings.json'

# 4. Version + self-update source
Copy-Item (Join-Path $src 'VERSION') (Join-Path $state 'VERSION') -Force
if ($autoUpdate) {
    Remove-Item (Join-Path $state 'auto-update-disabled') -ErrorAction SilentlyContinue
    $git = Get-Command git -ErrorAction SilentlyContinue
    if (-not $SelfUpdate -and $git) {
        $repo = $env:CLAUDE_AGENTS_REPO
        if (-not $repo) { $repo = (& git -C $src remote get-url origin 2>$null) }
        if (-not $repo) { $repo = $defaultRepo }
        $mirror = Join-Path $state 'src'
        $env:GIT_TERMINAL_PROMPT = '0'
        if (Test-Path (Join-Path $mirror '.git')) {
            & git -C $mirror remote set-url origin $repo
        } else {
            & git clone --quiet --no-checkout $repo $mirror 2>$null
            if ($LASTEXITCODE -eq 0) { Say "  self-update source: $repo" }
            else { Write-Warning "could not clone $repo; auto-update stays idle until it is reachable." }
        }
    }
    Write-Utf8 (Join-Path $state 'last-check') ([string][DateTimeOffset]::UtcNow.ToUnixTimeSeconds())
} else {
    New-Item -ItemType File -Force (Join-Path $state 'auto-update-disabled') | Out-Null
    Say "  auto-update: disabled"
}

Say ""
Say "Done ($((Read-Utf8 (Join-Path $src 'VERSION')).Trim())). Restart Claude Code (or reload VS Code), then run /agents and /hooks to verify."
