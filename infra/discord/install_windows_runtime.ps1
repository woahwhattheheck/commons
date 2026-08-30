[CmdletBinding()]
param(
    [switch]$CloudCutoverVerified,
    [switch]$TemporaryStandby
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$taskNames = @(
    "Commons Discord Live Bridge v1",
    "Commons Discord Main Watcher v1",
    "Commons Discord Health Watcher v1"
)

if ($CloudCutoverVerified) {
    # Preserve uninterrupted service: only retire the standby after a real
    # GitHub-hosted sync has succeeded with the production Discord secret.
    foreach ($name in $taskNames) {
        Stop-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue
        Unregister-ScheduledTask -TaskName $name -Confirm:$false -ErrorAction SilentlyContinue
    }
    Write-Output "CLOUD_ONLY: verified cloud relay active; Windows standby retired."
    Write-Output "Runtime: .github/workflows/commons-discord-cloud.yml"
    exit 0
}

if (-not $TemporaryStandby) {
    Write-Error "REFUSE_LOCAL_REACTIVATION: use GitHub Actions; -TemporaryStandby is emergency-only after storage health is established."
    exit 2
}

# Until cloud readback is proven, retain the working relay but remove the
# visible console bursts and unbounded restart/minute-loop policy that made the
# old runtime noisy. The Discord tasks are not established as a crash cause.
# This is an explicit emergency compatibility standby, not the target runtime.
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$identity = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$powershell = (Get-Command powershell.exe -ErrorAction Stop).Source
$bridgeRunner = Join-Path $PSScriptRoot "run_bridge_windows.ps1"
$mainRunner = Join-Path $PSScriptRoot "run_main_watcher_windows.ps1"
$healthScript = Join-Path $PSScriptRoot "health_watch_windows_runtime.ps1"

$logonTrigger = New-ScheduledTaskTrigger -AtLogOn -User $identity
$mainTrigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(15) `
    -RepetitionInterval (New-TimeSpan -Minutes 15)
$healthTrigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(5) `
    -RepetitionInterval (New-TimeSpan -Minutes 5)
$principal = New-ScheduledTaskPrincipal -UserId $identity -LogonType Interactive -RunLevel Limited
$bridgeSettings = New-ScheduledTaskSettingsSet -Hidden -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries -StartWhenAvailable -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 5) -ExecutionTimeLimit ([TimeSpan]::Zero)
$boundedSettings = New-ScheduledTaskSettingsSet -Hidden -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries -StartWhenAvailable -RestartCount 1 `
    -RestartInterval (New-TimeSpan -Minutes 5) -ExecutionTimeLimit (New-TimeSpan -Minutes 2)

foreach ($name in $taskNames) {
    Stop-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue
}

function New-HiddenPowerShellAction([string]$ScriptPath) {
    New-ScheduledTaskAction -Execute $powershell `
        -Argument ('-NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File "' + `
            $ScriptPath + '"') -WorkingDirectory $repoRoot
}

$bridgeTask = New-ScheduledTask -Action (New-HiddenPowerShellAction $bridgeRunner) `
    -Trigger $logonTrigger -Principal $principal -Settings $bridgeSettings `
    -Description "Temporary hidden Commons Discord standby pending proven cloud cutover"
Register-ScheduledTask -TaskName $taskNames[0] -InputObject $bridgeTask -Force | Out-Null

$watchTask = New-ScheduledTask -Action (New-HiddenPowerShellAction $mainRunner) `
    -Trigger @($logonTrigger, $mainTrigger) -Principal $principal -Settings $boundedSettings `
    -Description "Bounded hidden fast-forward watcher pending proven cloud cutover"
Register-ScheduledTask -TaskName $taskNames[1] -InputObject $watchTask -Force | Out-Null

$healthTask = New-ScheduledTask -Action (New-HiddenPowerShellAction $healthScript) `
    -Trigger @($logonTrigger, $healthTrigger) -Principal $principal -Settings $boundedSettings `
    -Description "Bounded hidden bridge health check pending proven cloud cutover"
Register-ScheduledTask -TaskName $taskNames[2] -InputObject $healthTask -Force | Out-Null

Start-ScheduledTask -TaskName $taskNames[0]
Start-ScheduledTask -TaskName $taskNames[1]
Start-Sleep -Seconds 5
Start-ScheduledTask -TaskName $taskNames[2]

Write-Output "STANDBY_SAFE: relay retained; every action hidden; watcher 15m; health 5m."
Get-ScheduledTask | Where-Object { $_.TaskName -like "Commons Discord * v1" } |
    Select-Object TaskName, State, TaskPath
