# SOURCE-INSPECTED launcher build, intended for GitHub-hosted windows-2022 runner.
# b1r3: no cmd.exe, nested cmd quoting, transient batch files, or lossy ASCII paths.
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$vswhere = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio/Installer/vswhere.exe'
if (!(Test-Path -LiteralPath $vswhere -PathType Leaf)) {
  throw 'vswhere.exe not found; install Visual Studio Build Tools with x64 C++ workload'
}

# vswhere may return several lines (avoid PowerShell array .Trim() surprises).
$instances = @(& $vswhere -latest -products '*' -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath)
if ($LASTEXITCODE -ne 0) { throw "vswhere failed: $LASTEXITCODE" }
$vs = @($instances | Where-Object { $_ -and $_.Trim() } | ForEach-Object { $_.Trim() }) | Select-Object -First 1
if (!$vs) { throw 'Visual C++ x64 compiler workload was not found' }

# Microsoft-supported native PowerShell developer shell. Initialize in the same
# PowerShell process so compiler, SDK, INCLUDE and LIB paths persist.
$devShell = Join-Path $vs 'Common7/Tools/Launch-VsDevShell.ps1'
if (!(Test-Path -LiteralPath $devShell -PathType Leaf)) {
  throw "Missing Visual Studio Developer PowerShell: $devShell"
}
& $devShell -Arch amd64 -HostArch amd64 -SkipAutomaticLocation
if (!$env:VSCMD_VER) { throw 'Visual Studio Developer PowerShell did not initialize (VSCMD_VER missing)' }
$cl = Get-Command 'cl.exe' -CommandType Application -ErrorAction Stop
if (!$cl) { throw 'Microsoft C/C++ compiler cl.exe not available after developer-shell initialization' }

New-Item -ItemType Directory -Path 'work/bin' -Force | Out-Null
$src = (Resolve-Path -LiteralPath 'launcher/GitHubDesktopPortable.cpp').Path
$outDir = (Resolve-Path -LiteralPath 'work/bin').Path
$out = Join-Path $outDir 'GitHubDesktopPortable.exe'
$obj = Join-Path $outDir 'GitHubDesktopPortable.obj'
if (Test-Path -LiteralPath $out) { throw "Refusing stale launcher build output: $out" }

Write-Host "MSVC developer environment: $env:VSCMD_VER"
Write-Host "Compiler: $($cl.Source)"
Write-Host "Launcher source: $src"
# Each translation unit needs its OWN object output. /Fo:<file> with multiple
# source files causes MSVC D8021; compile individually, link after both succeed.
$guardSource = (Resolve-Path -LiteralPath 'launcher/AuthProtocolGuard.cpp').Path
$guardObj = Join-Path $outDir 'AuthProtocolGuard.obj'
& $cl.Source /nologo /std:c++17 /EHsc /O2 /W4 /DUNICODE /D_UNICODE /c "/Fo:$obj" $src
$mainExit = $LASTEXITCODE
if ($mainExit -ne 0) { throw "MSVC launcher translation unit failed: $mainExit" }
& $cl.Source /nologo /std:c++17 /EHsc /O2 /W4 /DUNICODE /D_UNICODE /c "/Fo:$guardObj" $guardSource
$guardExit = $LASTEXITCODE
if ($guardExit -ne 0) { throw "MSVC auth protocol guard compilation failed: $guardExit" }
& $cl.Source /nologo "/Fe:$out" $obj $guardObj /link /SUBSYSTEM:WINDOWS user32.lib shell32.lib advapi32.lib
$exitCode = $LASTEXITCODE
if ($exitCode -ne 0) { throw "MSVC launcher linking failed: $exitCode" }
if (!(Test-Path -LiteralPath $out -PathType Leaf)) { throw 'MSVC did not emit GitHubDesktopPortable.exe' }

# Validate actual x64 PE header, not just the filename or MZ signature.
$stream = [System.IO.File]::OpenRead($out)
$reader = $null
try {
  $reader = [System.IO.BinaryReader]::new($stream)
  if ($stream.Length -lt 1024 -or $reader.ReadUInt16() -ne 0x5a4d) { throw 'Launcher output is not a valid PE/MZ file' }
  $stream.Position = 0x3c
  $pe = $reader.ReadInt32()
  if ($pe -lt 64 -or $pe + 6 -gt $stream.Length) { throw 'Launcher output has an invalid PE header offset' }
  $stream.Position = $pe
  if ($reader.ReadUInt32() -ne 0x00004550) { throw 'Launcher output missing PE signature' }
  if ($reader.ReadUInt16() -ne 0x8664) { throw 'Launcher output is not x64 PE' }
} finally {
  if ($null -ne $reader) { $reader.Dispose() }
  $stream.Dispose()
}
Write-Host "WINDOWS-COMPILED: Win64 launcher: $out"

# Headless, isolated HKCU protocol fixture; NEVER uses the real auth scheme.
$fixture = Join-Path $outDir 'auth-guard-fixture.exe'
$fixtureSource = (Resolve-Path -LiteralPath 'tests/auth_guard_fixture.cpp').Path
$fixtureObj = Join-Path $outDir 'auth_guard_fixture.obj'
& $cl.Source /nologo /std:c++17 /EHsc /O2 /W4 /c "/Fo:$fixtureObj" '/Ilauncher' $fixtureSource
$fixtureCompile = $LASTEXITCODE
if ($fixtureCompile -ne 0) { throw "Auth registry fixture compilation failed: $fixtureCompile" }
& $cl.Source /nologo "/Fe:$fixture" $fixtureObj $guardObj /link advapi32.lib user32.lib shell32.lib
$fixtureLink = $LASTEXITCODE
if ($fixtureLink -ne 0) { throw "Auth registry fixture linking failed: $fixtureLink" }
& $fixture
$fixtureExit = $LASTEXITCODE
if ($fixtureExit -ne 0) { throw "Headless auth protocol fixture failed: $fixtureExit" }
Write-Host 'AUTOMATED-RUNTIME-TESTED (Windows, isolated HKCU fixture): auth ownership and restoration'
