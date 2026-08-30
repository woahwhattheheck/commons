[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$identity = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$powershell = (Get-Command powershell.exe -ErrorAction Stop).Source
$bridgeRunner = Join-Path $PSScriptRoot "run_bridge_windows.ps1"
$mainRunner = Join-Path $PSScriptRoot "run_main_watcher_windows.ps1"
$logonTrigger = New-ScheduledTaskTrigger -AtLogOn -User $identity
$minuteTrigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) `
    -RepetitionInterval (New-TimeSpan -Minutes 1)
$principal = New-ScheduledTaskPrincipal -UserId $identity -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -StartWhenAvailable -RestartCount 99 -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit ([TimeSpan]::Zero)

foreach ($name in "Commons Discord Live Bridge v1", "Commons Discord Main Watcher v1", `
        "Commons Discord Health Watcher v1") {
    Stop-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue
}

$bridgeAction = New-ScheduledTaskAction -Execute $powershell `
    -Argument ('-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "' + `
        $bridgeRunner + '"') -WorkingDirectory $repoRoot
$bridgeTask = New-ScheduledTask -Action $bridgeAction -Trigger $logonTrigger `
    -Principal $principal -Settings $settings `
    -Description "Durable Commons Discord bridge with append-only replay"
Register-ScheduledTask -TaskName "Commons Discord Live Bridge v1" `
    -InputObject $bridgeTask -Force | Out-Null

$watchAction = New-ScheduledTaskAction -Execute $powershell `
    -Argument ('-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "' + `
        $mainRunner + '"') `
    -WorkingDirectory $repoRoot
$watchTask = New-ScheduledTask -Action $watchAction -Trigger @($logonTrigger, $minuteTrigger) `
    -Principal $principal -Settings $settings `
    -Description "Fast-forward the dedicated Commons runtime checkout to moving main"
Register-ScheduledTask -TaskName "Commons Discord Main Watcher v1" `
    -InputObject $watchTask -Force | Out-Null

$healthScript = Join-Path $PSScriptRoot "health_watch_windows_runtime.ps1"
$healthAction = New-ScheduledTaskAction -Execute $powershell `
    -Argument ('-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "' + `
        $healthScript + '"') `
    -WorkingDirectory $repoRoot
$healthTask = New-ScheduledTask -Action $healthAction -Trigger @($logonTrigger, $minuteTrigger) `
    -Principal $principal -Settings $settings `
    -Description "Health-check and restart only the Commons Discord bridge task"
Register-ScheduledTask -TaskName "Commons Discord Health Watcher v1" `
    -InputObject $healthTask -Force | Out-Null

Start-ScheduledTask -TaskName "Commons Discord Live Bridge v1"
Start-ScheduledTask -TaskName "Commons Discord Main Watcher v1"
Start-Sleep -Seconds 5
Start-ScheduledTask -TaskName "Commons Discord Health Watcher v1"

Get-ScheduledTask | Where-Object { $_.TaskName -like "Commons Discord * v1" } |
    Select-Object TaskName, State, TaskPath
