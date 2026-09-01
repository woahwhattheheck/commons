param(
    [string]$PythonExe = (Get-Command python -ErrorAction Stop).Source,
    [string]$OutputRoot = "",
    [switch]$SkipInstaller
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$spec = Join-Path $PSScriptRoot "ChartTrace.spec"
$manifestPath = Join-Path $PSScriptRoot "build_manifest.json"
$manifest = Get-Content $manifestPath -Raw | ConvertFrom-Json
$requiredPyInstaller = [string]$manifest.pyinstaller_version

if ($manifest.signing_state -ne "unsigned" -or
    $manifest.artifact_label -ne "UNSIGNED_SYNTHETIC" -or
    $manifest.production_distribution_authorized -ne $false) {
    throw "This build must remain explicitly unsigned and non-production."
}
if ([string]::IsNullOrWhiteSpace($OutputRoot)) {
    $OutputRoot = Join-Path $repoRoot "dist\charttrace-unsigned"
}
if (Test-Path -LiteralPath $OutputRoot) {
    $existing = @(Get-ChildItem -LiteralPath $OutputRoot -Force)
    if ($existing.Count -gt 0) {
        throw "OutputRoot must be new or empty; refusing to overwrite build evidence."
    }
} else {
    New-Item -ItemType Directory -Path $OutputRoot | Out-Null
}

$versionOutput = @(& $PythonExe -m PyInstaller --version 2>&1)
$versionExit = $LASTEXITCODE
if ($versionExit -ne 0 -or $versionOutput.Count -eq 0) {
    throw "Pinned PyInstaller $requiredPyInstaller is unavailable; the build script never installs dependencies automatically."
}
$pyInstallerVersion = ([string]$versionOutput[-1]).Trim()
if ($pyInstallerVersion -ne $requiredPyInstaller) {
    throw "Pinned PyInstaller $requiredPyInstaller is required; got '$pyInstallerVersion'."
}

$frozenDir = Join-Path $OutputRoot "frozen"
$workDir = Join-Path $OutputRoot "work"
$releaseDir = Join-Path $OutputRoot "release"
$buildLog = Join-Path $OutputRoot "pyinstaller-build.log"
New-Item -ItemType Directory -Path $frozenDir,$workDir,$releaseDir | Out-Null

Push-Location $repoRoot
try {
    $env:PYTHONHASHSEED = "0"
    $pyInstallerArgs = @(
        "-m", "PyInstaller", "--noconfirm",
        "--distpath", $frozenDir,
        "--workpath", $workDir,
        $spec
    )
    & $PythonExe @pyInstallerArgs 2>&1 | Tee-Object -FilePath $buildLog
    $buildExit = $LASTEXITCODE
    if ($buildExit -ne 0) {
        throw "PyInstaller failed with exit code $buildExit."
    }

    $exe = Join-Path $frozenDir "ChartTrace.exe"
    if (-not (Test-Path -LiteralPath $exe -PathType Leaf)) {
        throw "Pinned build did not produce ChartTrace.exe."
    }
    $signatureStatus = [string](Get-AuthenticodeSignature -LiteralPath $exe).Status
    if ($signatureStatus -ne "NotSigned") {
        throw "Unsigned build expected Authenticode status NotSigned; got $signatureStatus."
    }

    $receiptArgs = @(
        "-m", "charttrace.packaging.unsigned_artifact",
        "--exe", $exe,
        "--dest", $releaseDir,
        "--build-log", $buildLog,
        "--authenticode-status", $signatureStatus
    )
    & $PythonExe @receiptArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Exact frozen-executable smoke or artifact receipt failed."
    }

    if (-not $SkipInstaller) {
        $iscc = Get-Command "ISCC.exe" -ErrorAction SilentlyContinue
        if ($null -eq $iscc) {
            throw "Inno Setup is unavailable; rerun with -SkipInstaller for portable evidence only."
        } else {
            $installerDir = Join-Path $OutputRoot "installer"
            $innoLog = Join-Path $OutputRoot "inno-build.log"
            New-Item -ItemType Directory -Path $installerDir | Out-Null
            $innoArgs = @(
                "/DArtifactRoot=$releaseDir",
                "/DInstallerOutputDir=$installerDir",
                (Join-Path $PSScriptRoot "ChartTrace.iss")
            )
            & $iscc.Source @innoArgs 2>&1 | Tee-Object -FilePath $innoLog
            if ($LASTEXITCODE -ne 0) {
                throw "Inno Setup failed with exit code $LASTEXITCODE."
            }
        }
    }
}
finally {
    Pop-Location
}

Write-Host "Built and host-smoked the actual ChartTrace frozen executable."
Write-Host "Label: UNSIGNED_SYNTHETIC; production=false; signing_state=unsigned."
Write-Host "Clean-VM, installer lifecycle, accessibility, and Authenticode remain release gates."

