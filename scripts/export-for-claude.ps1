# Export Career OS for Claude (excludes secrets, node_modules, storage)
# Usage: .\scripts\export-for-claude.ps1

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$outZip = Join-Path (Split-Path -Parent $root) "career-os-claude-export.zip"
$staging = Join-Path $env:TEMP "career-os-claude-export-$(Get-Date -Format 'yyyyMMdd-HHmmss')"

Write-Host "Exporting Career OS from: $root"
Write-Host "Output: $outZip"

New-Item -ItemType Directory -Path $staging -Force | Out-Null

$excludeDirs = @(
    'node_modules', '.git', 'storage', 'dist', '__pycache__', '.pytest_cache',
    '.ruff_cache', '.mypy_cache', 'target', '.venv', 'venv', 'backups'
)
$excludeFiles = @('.env', '*.pyc', '*.pdf', '*.tar.gz', '*.zip')

function Should-Skip($relativePath) {
    $parts = $relativePath -split '[\\/]'
    foreach ($part in $parts) {
        if ($excludeDirs -contains $part) { return $true }
    }
    $name = Split-Path -Leaf $relativePath
    foreach ($pattern in $excludeFiles) {
        if ($name -like $pattern) { return $true }
    }
    return $false
}

function Copy-Filtered($src, $dest) {
    Get-ChildItem -Path $src -Recurse -Force -ErrorAction SilentlyContinue | ForEach-Object {
        $rel = $_.FullName.Substring($src.Length).TrimStart('\', '/')
        if ([string]::IsNullOrWhiteSpace($rel)) { return }
        if (Should-Skip $rel) { return }
        $target = Join-Path $dest $rel
        if ($_.PSIsContainer) {
            New-Item -ItemType Directory -Path $target -Force | Out-Null
        } else {
            $parent = Split-Path -Parent $target
            if (-not (Test-Path $parent)) { New-Item -ItemType Directory -Path $parent -Force | Out-Null }
            Copy-Item $_.FullName $target -Force
        }
    }
}

Copy-Filtered $root $staging

# Ensure brief is at top of staging
$brief = Join-Path $root "CLAUDE_PROJECT_BRIEF.md"
if (Test-Path $brief) {
    Copy-Item $brief (Join-Path $staging "START_HERE_CLAUDE_PROJECT_BRIEF.md") -Force
}

if (Test-Path $outZip) { Remove-Item $outZip -Force }
Compress-Archive -Path (Join-Path $staging '*') -DestinationPath $outZip -CompressionLevel Optimal

Remove-Item $staging -Recurse -Force

$sizeMb = [math]::Round((Get-Item $outZip).Length / 1MB, 2)
Write-Host ""
Write-Host "Done! Created: $outZip ($sizeMb MB)"
Write-Host ""
Write-Host "Upload to Claude:"
Write-Host "  1. Claude.ai -> Projects -> Create project"
Write-Host "  2. Add project knowledge -> Upload $outZip"
Write-Host "  3. Or paste CLAUDE_PROJECT_BRIEF.md in chat first"
Write-Host ""
Write-Host "See HOW_TO_FEED_CLAUDE.md for full instructions."
