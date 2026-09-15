Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
. (Join-Path $PSScriptRoot 'github_publish.ps1')

Write-Host ''
Write-Host '=============================================================' -ForegroundColor Magenta
Write-Host ' CTO STANDARDS WORKSPACE - PUBLISH ENTIRE LOCAL FOLDER' -ForegroundColor Magenta
Write-Host '=============================================================' -ForegroundColor Magenta
Write-Host "Local:  $Root" -ForegroundColor Cyan
Write-Host 'Target: https://github.com/ahmedlabib33-boop/CTO-Standards-Workspace' -ForegroundColor Cyan
Write-Host 'PowerShell will use repo_token.txt with the GitHub REST API; Git is not required.' -ForegroundColor Yellow
Write-Host 'repo_token.txt will never be uploaded and will be removed from GitHub if it was previously committed.' -ForegroundColor Yellow
Write-Host ''

Push-MainTree -Root $Root -Message ("chore: publish full CTO Standards Workspace tree {0}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'))
Write-Host ''
Write-Host 'SUCCESS: entire local folder published without Git.' -ForegroundColor Green
Write-Host 'repo_token.txt was excluded from the GitHub tree.' -ForegroundColor Green
Write-Host ''

Read-Host 'Press ENTER to close'
