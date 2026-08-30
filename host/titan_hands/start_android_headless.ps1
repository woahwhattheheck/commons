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

function Get-AdbEmulators {
    $records = @()
    foreach ($rawLine in @(& $adb devices 2>$null)) {
        $line = "$rawLine".Trim()
        if ($line -match '^(emulator-\d+)\s+(device|offline)$') {
            $records += [pscustomobject]@{
                serial = $Matches[1]
                state = $Matches[2]
            }
        }
    }
    return @($records)
}

function Get-ExactAvdProcesses {
    $plainArgument = "-avd $AvdName"
    $quotedArgument = "-avd `"$AvdName`""
    return @(Get-CimInstance -ClassName Win32_Process -Filter "Name = 'emulator.exe'" `
        -ErrorAction SilentlyContinue | Where-Object {
            $commandLine = "$($_.CommandLine)"
            $namesExactAvd =
                $commandLine.IndexOf($plainArgument, [System.StringComparison]::OrdinalIgnoreCase) -ge 0 -or
                $commandLine.IndexOf($quotedArgument, [System.StringComparison]::OrdinalIgnoreCase) -ge 0
            $namesExactAvd -and
                $commandLine.IndexOf('-no-window', [System.StringComparison]::OrdinalIgnoreCase) -ge 0
        })
}

# An interrupted host can leave the exact TITAN AVD process alive while ADB reports its transport as
# `offline`. Treating that as "no emulator" starts a second process on the same console port and converts a
# recoverable transport interruption into a persistent collision. Reconnect first; if the exact named
# headless process remains stale, recycle only that process. Userdata and AVD files are never removed or wiped.
$emulatorRecords = @(Get-AdbEmulators)
$online = $emulatorRecords | Where-Object { $_.state -eq 'device' } | Select-Object -First 1
$offline = @($emulatorRecords | Where-Object { $_.state -eq 'offline' })
$exactAvdProcesses = @(Get-ExactAvdProcesses)
$offlineReconnectAttempted = $false
$offlineProcessRestarted = $false
$recycledProcessIds = @()

if (-not $online -and ($offline.Count -gt 0 -or $exactAvdProcesses.Count -gt 0)) {
    $offlineReconnectAttempted = $true
    & $adb reconnect offline 2>$null | Out-Null
    $reconnectDeadline = [DateTime]::UtcNow.AddSeconds([Math]::Min(12, [Math]::Max(2, $TimeoutSeconds)))
    while ([DateTime]::UtcNow -lt $reconnectDeadline) {
        $emulatorRecords = @(Get-AdbEmulators)
        $online = $emulatorRecords | Where-Object { $_.state -eq 'device' } | Select-Object -First 1
        if ($online) { break }
        Start-Sleep -Seconds 1
    }
}

if (-not $online) {
    $exactAvdProcesses = @(Get-ExactAvdProcesses)
    foreach ($process in $exactAvdProcesses) {
        $liveProcess = Get-Process -Id $process.ProcessId -ErrorAction SilentlyContinue
        if ($liveProcess) {
            Stop-Process -Id $process.ProcessId -Force -PassThru |
                Wait-Process -Timeout 10 -ErrorAction SilentlyContinue
            if (Get-Process -Id $process.ProcessId -ErrorAction SilentlyContinue) {
                throw "Exact TITAN AVD process $($process.ProcessId) did not exit; refusing to start a duplicate emulator"
            }
            $recycledProcessIds += [int]$process.ProcessId
        }
    }
    if ($recycledProcessIds.Count -gt 0) {
        $offlineProcessRestarted = $true
        Start-Sleep -Seconds 1
    }
}

# Quick Boot stores a RAM image roughly as large as the emulator's memory floor. On a constrained host,
# that disposable cache can leave too little disk for the emulator to start. The dedicated TITAN AVD uses
# cold boots, so reclaim only its generated RAM cache when free space is low; userdata remains untouched.
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

function Start-ExactHeadlessEmulator {
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
    return Start-Process -FilePath $emulator -ArgumentList $arguments -WindowStyle Hidden `
        -RedirectStandardOutput $stdoutLog -RedirectStandardError $stderrLog -PassThru
}

function Wait-HeadlessBoot {
    param([System.Diagnostics.Process]$Process)

    $deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
    while ([DateTime]::UtcNow -lt $deadline) {
        if ($Process) {
            $Process.Refresh()
            if ($Process.HasExited) {
                $tail = Get-EmulatorLogTail
                throw "Headless Android emulator exited before ADB registration (exit $($Process.ExitCode)). $tail"
            }
        }
        $line = & $adb devices | Select-String -Pattern '^(emulator-\d+)\s+device$' | Select-Object -First 1
        if ($line) {
            $candidateSerial = $line.Matches[0].Groups[1].Value
            $booted = (& $adb -s $candidateSerial shell getprop sys.boot_completed 2>$null).Trim()
            if ($booted -eq '1') { return $candidateSerial }
        }
        Start-Sleep -Seconds 2
    }
    return $null
}

$emulatorProcess = $null
if (-not $online) {
    $emulatorProcess = Start-ExactHeadlessEmulator
}

$serial = Wait-HeadlessBoot -Process $emulatorProcess
$bootIncompleteProcessRestarted = $false
if (-not $serial -and -not $offlineProcessRestarted) {
    $exactAvdProcesses = @(Get-ExactAvdProcesses)
    foreach ($process in $exactAvdProcesses) {
        $liveProcess = Get-Process -Id $process.ProcessId -ErrorAction SilentlyContinue
        if ($liveProcess) {
            Stop-Process -Id $process.ProcessId -Force -PassThru |
                Wait-Process -Timeout 10 -ErrorAction SilentlyContinue
            if (Get-Process -Id $process.ProcessId -ErrorAction SilentlyContinue) {
                throw "Exact TITAN AVD process $($process.ProcessId) did not exit after incomplete boot; refusing to start a duplicate emulator"
            }
            $recycledProcessIds += [int]$process.ProcessId
        }
    }
    if ($exactAvdProcesses.Count -gt 0) {
        $bootIncompleteProcessRestarted = $true
        Start-Sleep -Seconds 1
        $emulatorProcess = Start-ExactHeadlessEmulator
        $serial = Wait-HeadlessBoot -Process $emulatorProcess
    }
}

if (-not $serial) {
    $tail = Get-EmulatorLogTail
    $recycled = if ($recycledProcessIds.Count -gt 0) { $recycledProcessIds -join ',' } else { 'none' }
    throw "Headless Android emulator did not boot. offline_reconnect_attempted=$offlineReconnectAttempted; offline_process_restarted=$offlineProcessRestarted; boot_incomplete_process_restarted=$bootIncompleteProcessRestarted; timeout_seconds_per_attempt=$TimeoutSeconds; recycled_process_ids=$recycled. $tail"
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
    offline_reconnect_attempted = $offlineReconnectAttempted
    offline_process_restarted = $offlineProcessRestarted
    boot_incomplete_process_restarted = $bootIncompleteProcessRestarted
    recycled_process_ids = @($recycledProcessIds)
    snapshot_cache_reclaimed_bytes = $snapshotCacheReclaimedBytes
    stdout_log = $stdoutLog
    stderr_log = $stderrLog
} | ConvertTo-Json -Compress
