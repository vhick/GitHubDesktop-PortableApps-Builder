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
  # BUILD DEPENDENCIES MUST BE PRESENT BEFORE THE UPSTREAM POSTINSTALL HOOK.
  # GitHub Desktop 3.6.10 declares @types/glob under root devDependencies.
  # Yarn Classic silently omits them if NODE_ENV=production during install.
  # The upstream postinstall also runs a nested Yarn install for app/.
  $env:NODE_ENV = 'development'
  # Use upstream-vendored Yarn Classic entrypoint to avoid moving package-manager baselines.
  $vendoredYarn = Get-ChildItem -LiteralPath 'vendor' -Filter 'yarn-*.js' -File | Sort-Object Name | Select-Object -Last 1
  if (!$vendoredYarn) { throw 'Upstream vendored Yarn is missing' }
  Write-Host 'Installing full frozen-lockfile build dependencies (including devDependencies)...'
  & node $vendoredYarn.FullName install --frozen-lockfile --non-interactive --production=false
  if ($LASTEXITCODE -ne 0) { throw "Upstream Yarn install failed: $LASTEXITCODE" }
  $globTypes = Join-Path $source 'node_modules/@types/glob/index.d.ts'
  if (!(Test-Path -LiteralPath $globTypes -PathType Leaf)) {
    throw 'Missing root @types/glob despite full Yarn install; refusing to run a broken TypeScript build'
  }
  # NODE_ENV=production belongs ONLY to webpack/build, not dependency installation.
  $env:NODE_ENV = 'production'
  Write-Host 'Compiling source with production build settings...'
  & node $vendoredYarn.FullName build:prod
  if ($LASTEXITCODE -ne 0) { throw "Upstream source build failed: $LASTEXITCODE" }
  $out = Join-Path $source 'dist/GitHubDesktop-win32-x64'
  if (!(Test-Path -LiteralPath (Join-Path $out 'GitHubDesktop.exe'))) { throw "Missing expected upstream build output: $out" }
  Write-Host "Source build created $out"
} finally { Pop-Location }
