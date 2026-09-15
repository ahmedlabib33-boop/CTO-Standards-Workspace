Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Publishes directly through the GitHub REST API.  Git.exe is deliberately not
# used, so the BAT launchers remain usable on machines where Git is not installed.
$script:GitHubOwner = 'ahmedlabib33-boop'
$script:GitHubRepository = 'CTO-Standards-Workspace'
$script:GitHubApiBase = 'https://api.github.com'
$script:GitHubApiVersion = '2022-11-28'
$script:AlwaysExcludedDirectoryNames = @('.git', '.next', '.vercel', 'node_modules', '__pycache__', '.venv', 'venv', 'out')
$script:AlwaysExcludedFileNames = @('repo_token.txt', 'vercel_deploy_hook.txt')

function Get-RepositoryRoot {
    return (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
}

function Get-RepositoryToken {
    param([Parameter(Mandatory = $true)][string]$Root)

    $tokenFile = Join-Path $Root 'repo_token.txt'
    if (-not (Test-Path -LiteralPath $tokenFile -PathType Leaf)) {
        throw "Missing repo_token.txt: $tokenFile"
    }

    $token = (Get-Content -LiteralPath $tokenFile -Raw).Trim()
    if ([string]::IsNullOrWhiteSpace($token) -or $token -eq 'PASTE_GITHUB_TOKEN_HERE') {
        throw 'repo_token.txt is empty or still contains the placeholder. Paste a GitHub token with write access to the configured repository, save it, then retry.'
    }
    return $token
}

function New-GitHubHeaders {
    param([Parameter(Mandatory = $true)][string]$Token)

    return @{
        Accept = 'application/vnd.github+json'
        Authorization = "Bearer $Token"
        'X-GitHub-Api-Version' = $script:GitHubApiVersion
        'User-Agent' = 'CTO-Standards-Workspace-PowerShell-Publisher'
    }
}

function Invoke-GitHubApi {
    param(
        [Parameter(Mandatory = $true)][ValidateSet('Get', 'Post', 'Patch', 'Put')][string]$Method,
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Token,
        [object]$Body
    )

    $request = @{
        Uri = "$script:GitHubApiBase$Path"
        Method = $Method
        Headers = (New-GitHubHeaders -Token $Token)
        ErrorAction = 'Stop'
    }
    if ($PSBoundParameters.ContainsKey('Body')) {
        $request.ContentType = 'application/json'
        $request.Body = ($Body | ConvertTo-Json -Depth 20 -Compress)
    }

    try {
        return Invoke-RestMethod @request
    } catch {
        $statusCode = $null
        if ($_.Exception.Response -and $_.Exception.Response.StatusCode) {
            $statusCode = [int]$_.Exception.Response.StatusCode
        }
        $detail = $_.Exception.Message
        if ($_.ErrorDetails -and -not [string]::IsNullOrWhiteSpace($_.ErrorDetails.Message)) {
            $detail = $_.ErrorDetails.Message
        }
        $exception = New-Object System.Exception("GitHub API $Method $Path failed: $detail")
        if ($null -ne $statusCode) {
            $exception.Data['GitHubStatusCode'] = $statusCode
        }
        throw $exception
    }
}

function Get-IgnoreRules {
    param([Parameter(Mandatory = $true)][string]$Root)

    $ignoreFile = Join-Path $Root '.gitignore'
    if (-not (Test-Path -LiteralPath $ignoreFile -PathType Leaf)) { return @() }

    return @(
        Get-Content -LiteralPath $ignoreFile |
            ForEach-Object { $_.Trim() } |
            Where-Object { $_ -and -not $_.StartsWith('#') }
    )
}

function Test-IgnoreRule {
    param(
        [Parameter(Mandatory = $true)][string]$RelativePath,
        [Parameter(Mandatory = $true)][string]$Rule,
        [switch]$IsDirectory
    )

    $normalizedPath = $RelativePath.Replace('\', '/').Trim('/')
    $normalizedRule = $Rule.Replace('\', '/').Trim()
    if (-not $normalizedRule) { return $false }
    if ($normalizedRule.StartsWith('/')) { $normalizedRule = $normalizedRule.TrimStart('/') }

    $directoryRule = $normalizedRule.EndsWith('/')
    if ($directoryRule) { $normalizedRule = $normalizedRule.TrimEnd('/') }
    if (-not $normalizedRule) { return $false }

    $hasSlash = $normalizedRule.Contains('/')
    $leafName = Split-Path -Path $normalizedPath -Leaf
    if ($directoryRule) {
        if ($hasSlash) {
            return $normalizedPath -eq $normalizedRule -or $normalizedPath.StartsWith("$normalizedRule/")
        }
        return @($normalizedPath.Split('/') | Where-Object { $_ -like $normalizedRule }).Count -gt 0
    }

    if (-not $hasSlash) { return $leafName -like $normalizedRule }
    return $normalizedPath -like $normalizedRule
}

function Test-PublishExclusion {
    param(
        [Parameter(Mandatory = $true)][string]$RelativePath,
        [string[]]$IgnoreRules = @(),
        [switch]$IsDirectory
    )

    $normalizedPath = $RelativePath.Replace('\', '/').Trim('/')
    if (-not $normalizedPath) { return $false }
    $segments = $normalizedPath.Split('/')
    if (@($segments | Where-Object { $script:AlwaysExcludedDirectoryNames -contains $_ }).Count -gt 0) {
        return $true
    }
    if (-not $IsDirectory -and ($script:AlwaysExcludedFileNames -contains $segments[-1])) {
        return $true
    }

    $ignored = $false
    foreach ($rawRule in $IgnoreRules) {
        $negated = $rawRule.StartsWith('!')
        $rule = if ($negated) { $rawRule.Substring(1) } else { $rawRule }
        if (Test-IgnoreRule -RelativePath $normalizedPath -Rule $rule -IsDirectory:$IsDirectory) {
            $ignored = -not $negated
        }
    }
    return $ignored
}

function Get-LocalRepositoryFiles {
    param([Parameter(Mandatory = $true)][string]$Root)

    $files = @{}
    $ignoreRules = Get-IgnoreRules -Root $Root

    function Visit-Directory {
        param([Parameter(Mandatory = $true)][System.IO.DirectoryInfo]$Directory)

        foreach ($entry in Get-ChildItem -LiteralPath $Directory.FullName -Force -ErrorAction Stop) {
            $relativePath = $entry.FullName.Substring($Root.Length).TrimStart('\', '/').Replace('\', '/')
            if ($entry.PSIsContainer) {
                if (($entry.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) { continue }
                if (-not (Test-PublishExclusion -RelativePath $relativePath -IgnoreRules $ignoreRules -IsDirectory)) {
                    Visit-Directory -Directory $entry
                }
            } elseif (-not (Test-PublishExclusion -RelativePath $relativePath -IgnoreRules $ignoreRules)) {
                $files[$relativePath] = $entry.FullName
            }
        }
    }

    Visit-Directory -Directory (Get-Item -LiteralPath $Root)
    return $files
}

function Get-GitBlobSha {
    param([Parameter(Mandatory = $true)][string]$Path)

    [byte[]]$content = [System.IO.File]::ReadAllBytes($Path)
    [byte[]]$header = [System.Text.Encoding]::UTF8.GetBytes("blob $($content.Length)$([char]0)")
    [byte[]]$blob = New-Object byte[] ($header.Length + $content.Length)
    [System.Buffer]::BlockCopy($header, 0, $blob, 0, $header.Length)
    [System.Buffer]::BlockCopy($content, 0, $blob, $header.Length, $content.Length)
    $sha1 = [System.Security.Cryptography.SHA1]::Create()
    try {
        return ([System.BitConverter]::ToString($sha1.ComputeHash($blob))).Replace('-', '').ToLowerInvariant()
    } finally {
        $sha1.Dispose()
    }
}

function New-GitHubBlob {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Token
    )

    $content = [Convert]::ToBase64String([System.IO.File]::ReadAllBytes($Path))
    $response = Invoke-GitHubApi -Method Post -Path "/repos/$script:GitHubOwner/$script:GitHubRepository/git/blobs" -Token $Token -Body @{
        content = $content
        encoding = 'base64'
    }
    return $response.sha
}

function Get-GitHubRepositoryState {
    param([Parameter(Mandatory = $true)][string]$Token)

    $branchPath = "/repos/$script:GitHubOwner/$script:GitHubRepository/git/ref/heads/main"
    try {
        $reference = Invoke-GitHubApi -Method Get -Path $branchPath -Token $Token
    } catch {
        # GitHub returns 409 ("Git Repository is empty") for an existing but
        # uninitialized repository, and 404 when the main ref is absent.
        if ($_.Exception.Data['GitHubStatusCode'] -in @(404, 409)) {
            return @{ CommitSha = $null; TreeSha = $null; Files = @{} }
        }
        throw
    }

    $commit = Invoke-GitHubApi -Method Get -Path "/repos/$script:GitHubOwner/$script:GitHubRepository/git/commits/$($reference.object.sha)" -Token $Token
    $tree = Invoke-GitHubApi -Method Get -Path "/repos/$script:GitHubOwner/$script:GitHubRepository/git/trees/$($commit.tree.sha)?recursive=1" -Token $Token
    if ($tree.truncated) {
        throw 'GitHub returned a truncated repository tree. Publishing stopped to prevent an incomplete snapshot.'
    }

    $files = @{}
    foreach ($entry in $tree.tree) {
        if ($entry.type -ne 'tree') { $files[$entry.path] = $entry }
    }
    return @{ CommitSha = $reference.object.sha; TreeSha = $commit.tree.sha; Files = $files }
}

function Initialize-EmptyGitHubRepository {
    param(
        [Parameter(Mandatory = $true)][hashtable]$LocalFiles,
        [Parameter(Mandatory = $true)][string]$Token
    )

    # The Git Blobs API cannot create the first object in an empty repository.
    # The Contents API can create the initial branch and commit, after which the
    # normal blob/tree/commit REST flow safely publishes the full snapshot.
    $bootstrapPath = $null
    foreach ($candidate in @('.gitignore', 'README.md')) {
        if ($LocalFiles.ContainsKey($candidate) -and (Get-Item -LiteralPath $LocalFiles[$candidate]).Length -gt 0) {
            $bootstrapPath = $candidate
            break
        }
    }
    if ($null -eq $bootstrapPath) {
        $bootstrapPath = $LocalFiles.Keys |
            Sort-Object |
            Where-Object { (Get-Item -LiteralPath $LocalFiles[$_]).Length -gt 0 } |
            Select-Object -First 1
    }
    if ([string]::IsNullOrWhiteSpace($bootstrapPath)) {
        throw 'The empty GitHub repository cannot be initialized because the workspace has no non-empty publishable file.'
    }

    $apiPath = ($bootstrapPath.Split('/') | ForEach-Object { [Uri]::EscapeDataString($_) }) -join '/'
    $content = [Convert]::ToBase64String([System.IO.File]::ReadAllBytes($LocalFiles[$bootstrapPath]))
    Write-Host ("Initializing empty GitHub repository main with {0}..." -f $bootstrapPath) -ForegroundColor Cyan
    Invoke-GitHubApi -Method Put -Path "/repos/$script:GitHubOwner/$script:GitHubRepository/contents/$apiPath" -Token $Token -Body @{
        message = 'chore: initialize CTO Standards Workspace main'
        content = $content
        branch = 'main'
    } | Out-Null
}

function Test-GitHubPublishAccess {
    param([string]$Root = (Get-RepositoryRoot))

    $token = Get-RepositoryToken -Root $Root
    $repository = Invoke-GitHubApi -Method Get -Path "/repos/$script:GitHubOwner/$script:GitHubRepository" -Token $token
    $canPush = $repository.permissions -and $repository.permissions.push
    if (-not $canPush) {
        throw 'The token can read the repository but does not have GitHub Contents write permission.'
    }
    return [pscustomobject]@{
        Repository = $repository.full_name
        DefaultBranch = $repository.default_branch
        CanPush = [bool]$canPush
    }
}

function Invoke-VercelPublish {
    param([Parameter(Mandatory = $true)][string]$Root)

    $hook = $env:VERCEL_DEPLOY_HOOK_URL
    $envFile = Join-Path $Root '.env.local'
    if ([string]::IsNullOrWhiteSpace($hook) -and (Test-Path -LiteralPath $envFile -PathType Leaf)) {
        $line = Get-Content -LiteralPath $envFile | Where-Object { $_ -match '^VERCEL_DEPLOY_HOOK_URL=' } | Select-Object -First 1
        if ($line) { $hook = $line.Substring('VERCEL_DEPLOY_HOOK_URL='.Length).Trim('"').Trim("'") }
    }

    if ([string]::IsNullOrWhiteSpace($hook)) {
        Write-Host 'No VERCEL_DEPLOY_HOOK_URL configured. A GitHub-connected Vercel project will deploy from the updated main branch.' -ForegroundColor DarkYellow
        return
    }

    Write-Host 'Triggering the optional Vercel deploy hook...' -ForegroundColor Cyan
    try {
        Invoke-RestMethod -Method Post -Uri $hook -ErrorAction Stop | Out-Null
        Write-Host 'Vercel deploy hook triggered.' -ForegroundColor Green
    } catch {
        Write-Warning "GitHub publication succeeded, but the Vercel deploy hook failed: $($_.Exception.Message)"
    }
}

function Push-MainTree {
    param(
        [string]$Root = (Get-RepositoryRoot),
        [string]$Message = 'chore: publish CTO Standards Workspace main tree',
        [switch]$SkipVercelHook,
        [switch]$WhatIf
    )

    $Root = (Resolve-Path -LiteralPath $Root).Path
    $localFiles = Get-LocalRepositoryFiles -Root $Root
    if ($localFiles.Count -eq 0) { throw 'No publishable files were found in the workspace.' }
    $token = Get-RepositoryToken -Root $Root
    $remote = Get-GitHubRepositoryState -Token $token
    if (-not $remote.CommitSha -and -not $WhatIf) {
        Initialize-EmptyGitHubRepository -LocalFiles $localFiles -Token $token
        $remote = Get-GitHubRepositoryState -Token $token
        if (-not $remote.CommitSha) { throw 'GitHub did not create main while initializing the empty repository.' }
    }

    $knownBlobShas = @{}
    foreach ($remoteFile in $remote.Files.Values) {
        if ($remoteFile.type -eq 'blob') { $knownBlobShas[$remoteFile.sha] = $true }
    }

    $treeChanges = New-Object System.Collections.Generic.List[object]
    foreach ($relativePath in $localFiles.Keys | Sort-Object) {
        $localPath = $localFiles[$relativePath]
        $localSha = Get-GitBlobSha -Path $localPath
        $remoteFile = $remote.Files[$relativePath]
        $mode = if ($remoteFile -and $remoteFile.mode -eq '100755') { '100755' } else { '100644' }
        if ($remoteFile -and $remoteFile.type -eq 'blob' -and $remoteFile.sha -eq $localSha -and $remoteFile.mode -eq $mode) {
            continue
        }
        if (-not $knownBlobShas.ContainsKey($localSha)) {
            if (-not $WhatIf) {
                $uploadedSha = New-GitHubBlob -Path $localPath -Token $token
                if ($uploadedSha -ne $localSha) { throw "GitHub returned an unexpected blob SHA for $relativePath." }
            }
            $knownBlobShas[$localSha] = $true
        }
        $treeChanges.Add([pscustomobject]@{ path = $relativePath; mode = $mode; type = 'blob'; sha = $localSha })
    }

    # This is a full workspace snapshot. It also removes a previously leaked
    # repo_token.txt from GitHub even though that local file is never uploaded.
    foreach ($relativePath in $remote.Files.Keys | Sort-Object) {
        if (-not $localFiles.ContainsKey($relativePath)) {
            $treeChanges.Add([pscustomobject]@{ path = $relativePath; mode = '100644'; type = 'blob'; sha = $null })
        }
    }

    if ($treeChanges.Count -eq 0) {
        Write-Host 'GitHub main already matches the publishable local workspace.' -ForegroundColor DarkGray
        return
    }

    if ($WhatIf) {
        Write-Host ("WhatIf: {0} path(s) would be committed to GitHub main; no GitHub changes were made." -f $treeChanges.Count) -ForegroundColor Yellow
        return [pscustomobject]@{ ChangedPaths = $treeChanges.Count; RemoteHead = $remote.CommitSha; Mode = 'WhatIf' }
    }

    Write-Host ("Publishing {0} changed path(s) to GitHub main through the REST API..." -f $treeChanges.Count) -ForegroundColor Cyan
    $treeBody = @{ tree = $treeChanges.ToArray() }
    if ($remote.TreeSha) { $treeBody.base_tree = $remote.TreeSha }
    $newTree = Invoke-GitHubApi -Method Post -Path "/repos/$script:GitHubOwner/$script:GitHubRepository/git/trees" -Token $token -Body $treeBody

    $commitBody = @{ message = $Message; tree = $newTree.sha }
    if ($remote.CommitSha) { $commitBody.parents = @($remote.CommitSha) }
    $commit = Invoke-GitHubApi -Method Post -Path "/repos/$script:GitHubOwner/$script:GitHubRepository/git/commits" -Token $token -Body $commitBody

    if ($remote.CommitSha) {
        Invoke-GitHubApi -Method Patch -Path "/repos/$script:GitHubOwner/$script:GitHubRepository/git/refs/heads/main" -Token $token -Body @{ sha = $commit.sha; force = $false } | Out-Null
    } else {
        Invoke-GitHubApi -Method Post -Path "/repos/$script:GitHubOwner/$script:GitHubRepository/git/refs" -Token $token -Body @{ ref = 'refs/heads/main'; sha = $commit.sha } | Out-Null
    }

    Write-Host ("GitHub main updated successfully: {0}" -f $commit.sha) -ForegroundColor Green
    if (-not $SkipVercelHook) { Invoke-VercelPublish -Root $Root }
}
