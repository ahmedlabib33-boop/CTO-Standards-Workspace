Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
. (Join-Path $PSScriptRoot 'publish_main.ps1')

Write-Host '=============================================================' -ForegroundColor Red
Write-Host ' CTO STANDARDS WORKSPACE - CLEAN GENERATED JSON' -ForegroundColor Red
Write-Host '=============================================================' -ForegroundColor Red
Write-Host 'Preserved: Excel sources, schema, admin overrides, source code.' -ForegroundColor Yellow
$answer = Read-Host 'Type CLEAN to continue'
if ($answer -ne 'CLEAN') { Write-Host 'Cancelled.'; exit 0 }

$generated = Join-Path $Root 'data\generated'
if (Test-Path $generated) {
    Get-ChildItem $generated -Recurse -File -Filter '*.json' -ErrorAction SilentlyContinue | Remove-Item -Force
    Get-ChildItem $generated -Recurse -Directory -ErrorAction SilentlyContinue |
        Sort-Object FullName -Descending |
        ForEach-Object {
            if (-not (Get-ChildItem $_.FullName -Force -ErrorAction SilentlyContinue | Select-Object -First 1)) {
                Remove-Item $_.FullName -Force
            }
        }
}
New-Item -ItemType Directory -Force -Path (Join-Path $generated 'master') | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $generated 'workbooks') | Out-Null

Push-MainTree -Message ("data: clean generated CTO Standards Workspace JSON {0}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'))
Write-Host 'Local and GitHub generated JSON state are synchronized.' -ForegroundColor Green
