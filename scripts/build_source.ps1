$ErrorActionPreference = 'Stop'
$source = (Resolve-Path -LiteralPath 'work/source').Path
$nodeVersion = (Get-Content -LiteralPath (Join-Path $source '.node-version') -Raw).Trim()
Write-Host "Source Node version: $nodeVersion"
Push-Location $source
try {
  $env:PYTHONUTF8 = '1'
  $env:PYTHONIOENCODING = 'utf-8'
  $env:GHD_PORTABLE_SOURCE_BUILD = '1'
  $env:RELEASE_CHANNEL = 'production'
  $env:NODE_ENV = 'production'
  # Use upstream-vendored Yarn Classic entrypoint to avoid moving package-manager baselines.
  $vendoredYarn = Get-ChildItem -LiteralPath 'vendor' -Filter 'yarn-*.js' -File | Sort-Object Name | Select-Object -Last 1
  if (!$vendoredYarn) { throw 'Upstream vendored Yarn is missing' }
  & node $vendoredYarn.FullName install --frozen-lockfile --non-interactive
  if ($LASTEXITCODE -ne 0) { throw "Upstream Yarn install failed: $LASTEXITCODE" }
  & node $vendoredYarn.FullName build:prod
  if ($LASTEXITCODE -ne 0) { throw "Upstream source build failed: $LASTEXITCODE" }
  $out = Join-Path $source 'dist/GitHubDesktop-win32-x64'
  if (!(Test-Path -LiteralPath (Join-Path $out 'GitHubDesktop.exe'))) { throw "Missing expected upstream build output: $out" }
  Write-Host "Source build created $out"
} finally { Pop-Location }
