$ErrorActionPreference = 'Stop'
$vswhere = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"
if (!(Test-Path -LiteralPath $vswhere)) { throw 'vswhere not found on Windows runner' }
$vs = (& $vswhere -latest -products '*' -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath).Trim()
if (!$vs) { throw 'Visual C++ x64 compiler not installed' }
$dev = Join-Path $vs 'VC/Auxiliary/Build/vcvars64.bat'
if (!(Test-Path -LiteralPath $dev)) { throw 'Missing vcvars64.bat' }
New-Item -ItemType Directory -Path 'work/bin' -Force | Out-Null
# A temporary batch file avoids brittle nested PowerShell/cmd quoting.
$batch = Join-Path (Resolve-Path 'work').Path 'compile-launcher.cmd'
$src = (Resolve-Path -LiteralPath 'launcher/GitHubDesktopPortable.cpp').Path
$out = Join-Path (Resolve-Path -LiteralPath 'work/bin').Path 'GitHubDesktopPortable.exe'
@(
  '@echo off',
  'call "' + $dev + '" >nul',
  'if errorlevel 1 exit /b 1',
  'cl.exe /nologo /std:c++17 /EHsc /O2 /W4 /DUNICODE /D_UNICODE "' + $src + '" /link /SUBSYSTEM:WINDOWS /OUT:"' + $out + '" shell32.lib user32.lib',
  'exit /b %errorlevel%'
) | Set-Content -LiteralPath $batch -Encoding ascii
& cmd.exe /D /C "`"$batch`""
if ($LASTEXITCODE -ne 0) { throw "MSVC launcher compilation failed: $LASTEXITCODE" }
if (!(Test-Path -LiteralPath $out)) { throw 'Compiler did not emit launcher PE' }
Write-Host "Windows launcher compiled: $out"
