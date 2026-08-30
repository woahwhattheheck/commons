[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$identity = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$python = (Get-Command python.exe -ErrorAction Stop).Source
$git = (Get-Command git.exe -ErrorAction Stop).Source
$logonTrigger = New-ScheduledTaskTrigger -AtLogOn -User $identity
$minuteTrigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) `
    -RepetitionInterval (New-TimeSpan -Minutes 1)
$principal = New-ScheduledTaskPrincipal -UserId $identity -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -StartWhenAvailable -RestartCount 99 -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit ([TimeSpan]::Zero)

foreach ($name in "Commons Discord Live Bridge v1", "Commons Discord Main Watcher v1") {
    Stop-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue
}

$bridgeAction = New-ScheduledTaskAction -Execute $python `
    -Argument '-B infra/discord/commons_discord_bridge.py' -WorkingDirectory $repoRoot
$bridgeTask = New-ScheduledTask -Action $bridgeAction -Trigger $logonTrigger `
    -Principal $principal -Settings $settings `
    -Description "Durable Commons Discord bridge with append-only replay"
Register-ScheduledTask -TaskName "Commons Discord Live Bridge v1" `
    -InputObject $bridgeTask -Force | Out-Null

$watchAction = New-ScheduledTaskAction -Execute $git `
    -Argument ('-C "' + $repoRoot + '" pull --ff-only --quiet origin main') `
    -WorkingDirectory $repoRoot
$watchTask = New-ScheduledTask -Action $watchAction -Trigger @($logonTrigger, $minuteTrigger) `
    -Principal $principal -Settings $settings `
    -Description "Fast-forward the dedicated Commons runtime checkout to moving main"
Register-ScheduledTask -TaskName "Commons Discord Main Watcher v1" `
    -InputObject $watchTask -Force | Out-Null

Start-ScheduledTask -TaskName "Commons Discord Live Bridge v1"
Start-ScheduledTask -TaskName "Commons Discord Main Watcher v1"

Get-ScheduledTask | Where-Object { $_.TaskName -like "Commons Discord * v1" } |
    Select-Object TaskName, State, TaskPath
