# Installs the Claude Code enterprise agent team globally (all projects) on Windows.
# Usage:  powershell -ExecutionPolicy Bypass -File .\install.ps1
param(
    [string]$ClaudeHome = (Join-Path $env:USERPROFILE '.claude')
)
$ErrorActionPreference = 'Stop'

$src     = Split-Path -Parent $MyInvocation.MyCommand.Path
$fwd     = $ClaudeHome -replace '\\', '/'
$stamp   = Get-Date -Format 'yyyyMMdd-HHmmss'
$utf8    = New-Object System.Text.UTF8Encoding $false
$marker  = 'prompt-reminder.txt'

function Write-Utf8([string]$path, [string]$text) {
    [System.IO.File]::WriteAllText($path, $text, $utf8)
}
function Backup-IfExists([string]$path) {
    if (Test-Path $path) {
        Copy-Item $path "$path.bak-$stamp"
        Write-Host "  backup: $path.bak-$stamp"
    }
}

Write-Host "Installing into $ClaudeHome"
foreach ($d in 'agents', 'commands', 'standards', 'hooks') {
    New-Item -ItemType Directory -Force (Join-Path $ClaudeHome $d) | Out-Null
}

# 1. Agents, command, standard, hook text (placeholder -> real path)
$files = @(
    'agents/planner.md', 'agents/researcher.md', 'agents/coder.md',
    'agents/reviewer.md', 'agents/cleaner.md', 'commands/build.md',
    'standards/ai-security.md', 'hooks/prompt-reminder.txt'
)
foreach ($f in $files) {
    $dest = Join-Path $ClaudeHome $f
    Backup-IfExists $dest
    $text = [System.IO.File]::ReadAllText((Join-Path $src $f), $utf8)
    Write-Utf8 $dest ($text.Replace('__CLAUDE_HOME__', $fwd))
    Write-Host "  installed: $f"
}

# 2. Global CLAUDE.md: replace our marked block, or append it; never drop user content
$claudeMd = Join-Path $ClaudeHome 'CLAUDE.md'
$block = [System.IO.File]::ReadAllText((Join-Path $src 'CLAUDE.global.md'), $utf8).Replace('__CLAUDE_HOME__', $fwd).Trim()
if (Test-Path $claudeMd) {
    Backup-IfExists $claudeMd
    $existing = [System.IO.File]::ReadAllText($claudeMd, $utf8)
    $pattern = '(?s)<!-- BEGIN claude-enterprise-agents -->.*?<!-- END claude-enterprise-agents -->'
    if ($existing -match $pattern) {
        $new = [regex]::Replace($existing, $pattern, { param($m) $block })
    } else {
        $new = $existing.TrimEnd() + "`r`n`r`n" + $block + "`r`n"
    }
    Write-Utf8 $claudeMd $new
} else {
    Write-Utf8 $claudeMd ($block + "`r`n")
}
Write-Host "  updated: CLAUDE.md"

# 3. settings.json: add UserPromptSubmit hook (merge, keep everything else)
$settingsPath = Join-Path $ClaudeHome 'settings.json'
if (Test-Path $settingsPath) {
    Backup-IfExists $settingsPath
    $raw = [System.IO.File]::ReadAllText($settingsPath, $utf8)
    if ($raw.Trim()) { $settings = $raw | ConvertFrom-Json } else { $settings = New-Object PSObject }
} else {
    $settings = New-Object PSObject
}
if (-not ($settings.PSObject.Properties.Name -contains 'hooks')) {
    $settings | Add-Member -NotePropertyName hooks -NotePropertyValue (New-Object PSObject)
}
$existingUps = @()
if ($settings.hooks.PSObject.Properties.Name -contains 'UserPromptSubmit') {
    $existingUps = @($settings.hooks.UserPromptSubmit)
}
$already = $existingUps | Where-Object { $_.hooks | Where-Object { $_.command -like "*$marker*" } }
if ($already) {
    Write-Host "  hook already present in settings.json, skipped"
} else {
    $entry = [pscustomobject]@{
        hooks = @([pscustomobject]@{
            type    = 'command'
            command = "cat `"$fwd/hooks/$marker`""
            timeout = 10
        })
    }
    $ups = @($existingUps) + $entry
    if ($settings.hooks.PSObject.Properties.Name -contains 'UserPromptSubmit') {
        $settings.hooks.UserPromptSubmit = $ups
    } else {
        $settings.hooks | Add-Member -NotePropertyName UserPromptSubmit -NotePropertyValue $ups
    }
    Write-Utf8 $settingsPath ($settings | ConvertTo-Json -Depth 50)
    Write-Host "  added hook to settings.json"
}

# Validate the result parses
$null = [System.IO.File]::ReadAllText($settingsPath, $utf8) | ConvertFrom-Json
Write-Host ""
Write-Host "Done. Restart Claude Code (or reload VS Code), then run /agents and /hooks to verify."
