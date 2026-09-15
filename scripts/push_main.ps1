Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
. (Join-Path $PSScriptRoot 'publish_main.ps1')
Push-MainTree -Message ("chore: publish CTO Standards Workspace main tree {0}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'))
Write-Host 'Main tree pushed successfully.' -ForegroundColor Green
