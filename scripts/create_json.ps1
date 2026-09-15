Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
. (Join-Path $PSScriptRoot 'publish_main.ps1')

Write-Host '=============================================================' -ForegroundColor Cyan
Write-Host ' CTO STANDARDS WORKSPACE - CREATE JSON + COMMIT + PUSH' -ForegroundColor Cyan
Write-Host '=============================================================' -ForegroundColor Cyan

$ExcelFiles = Get-ChildItem (Join-Path $Root 'data') -File |
    Where-Object { $_.Extension -in '.xlsx','.xlsm' -and -not $_.Name.StartsWith('~$') }

if ($ExcelFiles.Count -eq 0) { throw 'No Excel files found in data folder.' }

Write-Host 'Excel sources:' -ForegroundColor Yellow
$ExcelFiles | ForEach-Object { Write-Host "  $($_.Name)" }

$Python = Get-Command python -ErrorAction SilentlyContinue
if (-not $Python) { throw 'Python is not available in PATH.' }

Write-Host '1) Excel -> governed JSON' -ForegroundColor Cyan
python (Join-Path $Root 'scripts\excel_to_json.py') --data-dir (Join-Path $Root 'data')
if ($LASTEXITCODE -ne 0) { throw 'JSON generation failed.' }

Write-Host '2) Commit complete main tree and push to:' -ForegroundColor Cyan
Write-Host '   https://github.com/ahmedlabib33-boop/CTO-Standards-Workspace' -ForegroundColor Green
Push-MainTree -Message ("data: regenerate CTO Standards Workspace JSON {0}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'))

Write-Host '3) Vercel: Git-connected deployments will follow the main push.' -ForegroundColor Cyan
Write-Host 'Done.' -ForegroundColor Green
