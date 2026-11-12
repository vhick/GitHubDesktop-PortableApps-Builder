param([Parameter(Mandatory)][string]$Tag, [string]$Source = 'work/source')
$ErrorActionPreference = 'Stop'
if ($Tag -notmatch '^release-\d+\.\d+\.\d+$') { throw 'Unsafe/nonstable tag' }
if (Test-Path -LiteralPath $Source) { throw "Source path already exists: $Source" }
New-Item -ItemType Directory -Path $Source -Force | Out-Null
& git -C $Source init --quiet
if ($LASTEXITCODE -ne 0) { throw 'git init failed' }
& git -C $Source remote add origin https://github.com/desktop/desktop.git
if ($LASTEXITCODE -ne 0) { throw 'git remote failed' }
& git -C $Source fetch --quiet --depth=1 origin "refs/tags/${Tag}"
if ($LASTEXITCODE -ne 0) { throw 'Git fetch exact stable upstream tag failed' }
& git -C $Source checkout --quiet --detach FETCH_HEAD
if ($LASTEXITCODE -ne 0) { throw 'Git tag checkout failed' }
$commit = (& git -C $Source rev-parse 'HEAD').Trim()
if ($LASTEXITCODE -ne 0 -or $commit -notmatch '^[a-f0-9]{40}$') { throw 'Invalid git commit identity' }
$node = (Get-Content -LiteralPath (Join-Path $Source '.node-version') -Raw).Trim()
$lockfile = Join-Path $Source 'yarn.lock'
if (!(Test-Path -LiteralPath $lockfile)) { throw 'Missing expected yarn.lock' }
$lockSha = (Get-FileHash -LiteralPath $lockfile -Algorithm SHA256).Hash.ToLowerInvariant()
$meta = [ordered]@{ tag=$Tag; commit=$commit; node_version=$node; yarn_lock_sha256=$lockSha }
New-Item -ItemType Directory -Path work -Force | Out-Null
$meta | ConvertTo-Json | Set-Content -LiteralPath 'work/source-identity.json' -Encoding utf8
Write-Host "Verified source tag $Tag at commit $commit; yarn.lock SHA256 $lockSha; Node $node"
