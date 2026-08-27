[CmdletBinding()]
param(
    [string]$SdkRoot = $(if ($env:ANDROID_HOME) { $env:ANDROID_HOME } else { Join-Path $env:LOCALAPPDATA 'TitanHands\AndroidSdk' }),
    [string]$AndroidUserHome = $(if ($env:ANDROID_USER_HOME) { $env:ANDROID_USER_HOME } else { Join-Path $env:LOCALAPPDATA 'TitanHands\AndroidHome' }),
    [string]$AvdName = $(if ($env:TITAN_HANDS_ANDROID_AVD) { $env:TITAN_HANDS_ANDROID_AVD } else { 'TitanHands_AOSP_API34' }),
    [int]$TimeoutSeconds = 240
)

$ErrorActionPreference = 'Stop'
$emulator = Join-Path $SdkRoot 'emulator\emulator.exe'
$adb = Join-Path $SdkRoot 'platform-tools\adb.exe'
if (-not (Test-Path -LiteralPath $emulator)) { throw "Android emulator missing: $emulator" }
if (-not (Test-Path -LiteralPath $adb)) { throw "ADB missing: $adb" }

$env:ANDROID_HOME = [System.IO.Path]::GetFullPath($SdkRoot)
$env:ANDROID_USER_HOME = [System.IO.Path]::GetFullPath($AndroidUserHome)
$env:ANDROID_AVD_HOME = Join-Path $env:ANDROID_USER_HOME 'avd'
$avdRoot = [System.IO.Path]::GetFullPath((Join-Path $env:ANDROID_AVD_HOME ($AvdName + '.avd')))
$avdConfig = Join-Path $avdRoot 'config.ini'
if (Test-Path -LiteralPath $avdConfig) {
    $configText = Get-Content -LiteralPath $avdConfig -Raw
    $configText = $configText -replace '(?m)^disk\.dataPartition\.size=.*$', 'disk.dataPartition.size=2G'
    $configText = $configText -replace '(?m)^hw\.ramSize=.*$', 'hw.ramSize=1536'
    $configText = $configText -replace '(?m)^sdcard\.size=.*$', 'sdcard.size=256 MB'
    Set-Content -LiteralPath $avdConfig -Value $configText -Encoding Ascii
}

# Quick Boot stores a RAM image roughly as large as the emulator's memory floor. On a constrained host,
# that disposable cache can leave too little disk for the emulator to start. The dedicated TITAN AVD uses
# cold boots, so reclaim only its generated RAM cache when free space is low; userdata remains untouched.
$online = & $adb devices | Select-String -Pattern '^emulator-\d+\s+device$'
$snapshotCacheReclaimedBytes = 0L
$snapshotRam = [System.IO.Path]::GetFullPath((Join-Path $avdRoot 'snapshots\default_boot\ram.img'))
$avdDrive = [System.IO.DriveInfo]::new([System.IO.Path]::GetPathRoot($avdRoot))
if (-not $online -and $avdDrive.AvailableFreeSpace -lt 4GB -and (Test-Path -LiteralPath $snapshotRam -PathType Leaf)) {
    if (-not $snapshotRam.StartsWith($avdRoot + [System.IO.Path]::DirectorySeparatorChar, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to reclaim a snapshot cache outside the TITAN AVD: $snapshotRam"
    }
    $snapshotCacheReclaimedBytes = (Get-Item -LiteralPath $snapshotRam).Length
    $stream = [System.IO.File]::Open(
        $snapshotRam,
        [System.IO.FileMode]::Open,
        [System.IO.FileAccess]::Write,
        [System.IO.FileShare]::None
    )
    try { $stream.SetLength(0) } finally { $stream.Dispose() }
}

$logRoot = Join-Path $env:ANDROID_USER_HOME 'logs'
New-Item -ItemType Directory -Force -Path $logRoot | Out-Null
$stdoutLog = Join-Path $logRoot ($AvdName + '.stdout.log')
$stderrLog = Join-Path $logRoot ($AvdName + '.stderr.log')

function Get-EmulatorLogTail {
    $lines = @()
    foreach ($path in @($stderrLog, $stdoutLog)) {
        if (Test-Path -LiteralPath $path) {
            $lines += Get-Content -LiteralPath $path -Tail 20 -ErrorAction SilentlyContinue
        }
    }
    return (($lines | Where-Object { $_ }) -join ' | ')
}

$emulatorProcess = $null
if (-not $online) {
    [System.IO.File]::WriteAllText($stdoutLog, '')
    [System.IO.File]::WriteAllText($stderrLog, '')
    $arguments = @(
        '-avd', $AvdName,
        '-no-window',
        '-no-audio',
        '-no-boot-anim',
        '-gpu', 'swiftshader_indirect',
        '-memory', '1536',
        '-cores', '2',
        '-no-snapshot',
        '-no-snapstorage',
        '-feature', '-QuickbootFileBacked'
    )
    $emulatorProcess = Start-Process -FilePath $emulator -ArgumentList $arguments -WindowStyle Hidden `
        -RedirectStandardOutput $stdoutLog -RedirectStandardError $stderrLog -PassThru
}

$deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
$serial = $null
while ([DateTime]::UtcNow -lt $deadline) {
    if ($emulatorProcess) {
        $emulatorProcess.Refresh()
        if ($emulatorProcess.HasExited) {
            $tail = Get-EmulatorLogTail
            throw "Headless Android emulator exited before ADB registration (exit $($emulatorProcess.ExitCode)). $tail"
        }
    }
    $line = & $adb devices | Select-String -Pattern '^(emulator-\d+)\s+device$' | Select-Object -First 1
    if ($line) {
        $serial = $line.Matches[0].Groups[1].Value
        $booted = (& $adb -s $serial shell getprop sys.boot_completed 2>$null).Trim()
        if ($booted -eq '1') { break }
    }
    Start-Sleep -Seconds 2
}
if (-not $serial -or (& $adb -s $serial shell getprop sys.boot_completed 2>$null).Trim() -ne '1') {
    $tail = Get-EmulatorLogTail
    throw "Headless Android emulator did not boot within $TimeoutSeconds seconds. $tail"
}

& $adb -s $serial shell settings put global window_animation_scale 0 | Out-Null
& $adb -s $serial shell settings put global transition_animation_scale 0 | Out-Null
& $adb -s $serial shell settings put global animator_duration_scale 0 | Out-Null
& $adb -s $serial shell svc power stayon true | Out-Null

[pscustomobject]@{
    ok = $true
    serial = $serial
    avd = $AvdName
    display = 'headless'
    pixels = 'on-demand-only'
    snapshot_cache_reclaimed_bytes = $snapshotCacheReclaimedBytes
    stdout_log = $stdoutLog
    stderr_log = $stderrLog
} | ConvertTo-Json -Compress
