param([Parameter(Mandatory)][string]$Installer, [Parameter(Mandatory)][string]$ExpectedSha)
$ErrorActionPreference = 'Stop'
if (!(Test-Path -LiteralPath $Installer -PathType Leaf)) { throw "Missing installer: $Installer" }
$sha = (Get-FileHash -LiteralPath $Installer -Algorithm SHA256).Hash.ToLowerInvariant()
if ($sha -ne $ExpectedSha.ToLowerInvariant()) { throw "Installer checksum mismatch: $Installer" }
$f = [IO.File]::OpenRead((Resolve-Path -LiteralPath $Installer).Path)
try {
  $r = [IO.BinaryReader]::new($f)
  if ($f.Length -lt 1024 -or $r.ReadUInt16() -ne 0x5A4D) { throw 'Installer is not MZ/PE' }
  $f.Position = 0x3c
  $off = $r.ReadInt32()
  if ($off -lt 64 -or $off + 4 -ge $f.Length) { throw 'Invalid installer PE offset' }
  $f.Position = $off
  if ($r.ReadUInt32() -ne 0x4550) { throw 'Invalid installer PE signature' }
} finally { $f.Dispose() }
$seven = Get-Command 7z.exe -ErrorAction SilentlyContinue | Select-Object -First 1
$sevenPath = if ($seven) { $seven.Source } else { 'C:\Program Files\7-Zip\7z.exe' }
if (!(Test-Path -LiteralPath $sevenPath)) { throw '7-Zip missing: cannot independently validate embedded installer payload' }
& $sevenPath t -bso0 -bsp0 $Installer | Out-Host
if ($LASTEXITCODE -ne 0) { throw '7-Zip archive validation failed' }
$listing = (& $sevenPath l -slt $Installer) -join "`n"
if ($LASTEXITCODE -ne 0 -or $listing -notmatch 'GitHubDesktopPortable\.exe' -or $listing -notmatch 'appinfo\.ini') {
  throw 'Installer missing expected embedded launcher/appinfo layout'
}
Write-Host "STATIC-VALIDATED: installer PE + hash + 7z archive + launcher metadata: $sha"
