Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
# Compatibility entry point for older callers. The implementation now uses the
# GitHub REST API directly and does not require Git.exe.
. (Join-Path $PSScriptRoot 'github_publish.ps1')

function Publish-SamcoData {
    param(
        [string]$Root = (Get-RepositoryRoot),
        [string]$CommitMessage = 'data: publish CTO Standards Workspace JSON',
        [string[]]$Paths = @('data', '.gitignore')
    )
    Push-MainTree -Root $Root -Message $CommitMessage
}
