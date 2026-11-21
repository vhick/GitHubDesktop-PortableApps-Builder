# Read-only GitHub Desktop PortableApps OAuth handoff diagnostics.
# Never reads or prints callback URLs, OAuth codes, tokens, passwords, or credential data.
param([Parameter(Mandatory=$true)][string]$PortableRoot)
$ErrorActionPreference = 'Stop'
$root = [IO.Path]::GetFullPath($PortableRoot)
$launcher = [IO.Path]::GetFullPath((Join-Path $root 'GitHubDesktopPortable.exe'))
$data = Join-Path $root 'Data'
$statusFile = Join-Path $data 'TraceGuard/AuthProtocolStatus.txt'
$reportFile = Join-Path $data 'TraceGuard/AuthDiagnostics.txt'
$scheme = 'x-github-desktop-dev-auth'
$schemePath = 'Registry::HKEY_CURRENT_USER\Software\Classes\' + $scheme
$commandSuffix = '\shell\open\command'
$userChoice = 'Registry::HKEY_CURRENT_USER\Software\Microsoft\Windows\Shell\Associations\UrlAssociations\' + $scheme + '\UserChoice'
function Read-DefaultCommand([string]$registryPath) {
  try {
    $key = Get-Item -LiteralPath $registryPath -ErrorAction Stop
    return [string]$key.GetValue('', '')
  } catch { return '' }
}
function Matches-ThisLauncher([string]$command) {
  if ([string]::IsNullOrWhiteSpace($command)) { return $false }
  $expected = '"' + $launcher + '" --protocol-launcher "%1"'
  return $command.Equals($expected, [StringComparison]::OrdinalIgnoreCase)
}
$perUserCmd = Read-DefaultCommand ($schemePath + $commandSuffix)
$effectiveCmd = Read-DefaultCommand ('Registry::HKEY_CLASSES_ROOT\' + $scheme + $commandSuffix)
$hasUserChoice = Test-Path -LiteralPath $userChoice
$consentFile = Join-Path $data 'AuthRedirectConsent.txt'
$consent = if (Test-Path -LiteralPath $consentFile) {
  (Get-Content -LiteralPath $consentFile -TotalCount 1).Trim() -eq 'enabled'
} else { $false }
$lastStatuses = @()
if (Test-Path -LiteralPath $statusFile) {
  # Status file is written by this specific launcher and contains no callback arguments.
  # Keep only known fixed label prefixes; ignore unknown/raw messages completely.
  $labels = @('AUTH HANDLER ACTIVE:', 'CALLBACK INVOKED:', 'CALLBACK SPAWN FAILED:',
              'CLEAN EXIT:', 'SIGN-IN UNAVAILABLE:', 'RECOVERY CONFLICT:',
              'LEGACY AUTH RECOVERY CONFLICT:', 'HOST HANDLER PRESERVED:',
              'PROCESS TRACKING FAILED:')
  foreach ($line in (Get-Content -LiteralPath $statusFile -Tail 30)) {
    foreach ($label in $labels) {
      if ($line.StartsWith($label, [StringComparison]::Ordinal)) {
        $lastStatuses += $label
        break
      }
    }
  }
}
$lines = @(
 'GitHub Desktop Portable b1r6 - read-only browser sign-in diagnostics',
 'Expected callback scheme: x-github-desktop-dev-auth',
 'Launcher exists: ' + [bool](Test-Path -LiteralPath $launcher -PathType Leaf),
 'User consent enabled: ' + $consent,
 'Current-user scheme has a command: ' + [bool](-not [string]::IsNullOrEmpty($perUserCmd)),
 'Current-user command matches this root launcher: ' + (Matches-ThisLauncher $perUserCmd),
 'Effective HKCR scheme has a command: ' + [bool](-not [string]::IsNullOrEmpty($effectiveCmd)),
 'Effective HKCR command matches this root launcher: ' + (Matches-ThisLauncher $effectiveCmd),
 'Windows UserChoice exists for scheme: ' + $hasUserChoice,
 'Observed launcher status labels (no raw data):',
 ($lastStatuses -join ', ')
)
New-Item -ItemType Directory -Path (Split-Path -Parent $reportFile) -Force | Out-Null
$lines | Out-File -LiteralPath $reportFile -Encoding UTF8
$lines | Write-Output
Write-Output 'Report written in Data\TraceGuard\AuthDiagnostics.txt (no callback URLs or tokens).'
