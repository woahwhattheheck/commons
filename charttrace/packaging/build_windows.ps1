param(
    [switch]$SkipInstaller
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$spec = Join-Path $PSScriptRoot "ChartTrace.spec"
$manifest = Get-Content (Join-Path $PSScriptRoot "build_manifest.json") -Raw |
    ConvertFrom-Json

if ($manifest.signing_state -ne "unsigned" -or
    $manifest.artifact_label -ne "UNSIGNED_SYNTHETIC") {
    throw "The v1.1 synthetic build must remain explicitly unsigned."
}

Push-Location $repoRoot
try {
    py -m PyInstaller --clean --noconfirm $spec
    if (-not $SkipInstaller) {
        $iscc = Get-Command "ISCC.exe" -ErrorAction Stop
        & $iscc.Source "/DSourceRoot=$repoRoot" `
            (Join-Path $PSScriptRoot "ChartTrace.iss")
    }
}
finally {
    Pop-Location
}

Write-Host "Built ChartTrace 1.1 UNSIGNED_SYNTHETIC (signing_state=unsigned)."
