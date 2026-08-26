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
$avdConfig = Join-Path $env:ANDROID_AVD_HOME ($AvdName + '.avd\config.ini')
if (Test-Path -LiteralPath $avdConfig) {
    $configText = Get-Content -LiteralPath $avdConfig -Raw
    $configText = $configText -replace '(?m)^disk\.dataPartition\.size=.*$', 'disk.dataPartition.size=2G'
    $configText = $configText -replace '(?m)^hw\.ramSize=.*$', 'hw.ramSize=1536'
    $configText = $configText -replace '(?m)^sdcard\.size=.*$', 'sdcard.size=256 MB'
    Set-Content -LiteralPath $avdConfig -Value $configText -Encoding Ascii
}
$online = & $adb devices | Select-String -Pattern '^emulator-\d+\s+device$'
if (-not $online) {
    $arguments = @(
        '-avd', $AvdName,
        '-no-window',
        '-no-audio',
        '-no-boot-anim',
        '-gpu', 'swiftshader_indirect',
        '-memory', '1536',
        '-cores', '2'
    )
    Start-Process -FilePath $emulator -ArgumentList $arguments -WindowStyle Hidden | Out-Null
}

$deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
$serial = $null
while ([DateTime]::UtcNow -lt $deadline) {
    $line = & $adb devices | Select-String -Pattern '^(emulator-\d+)\s+device$' | Select-Object -First 1
    if ($line) {
        $serial = $line.Matches[0].Groups[1].Value
        $booted = (& $adb -s $serial shell getprop sys.boot_completed 2>$null).Trim()
        if ($booted -eq '1') { break }
    }
    Start-Sleep -Seconds 2
}
if (-not $serial -or (& $adb -s $serial shell getprop sys.boot_completed 2>$null).Trim() -ne '1') {
    throw "Headless Android emulator did not boot within $TimeoutSeconds seconds"
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
} | ConvertTo-Json -Compress
