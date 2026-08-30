[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$python = (Get-Command python.exe -ErrorAction Stop).Source
$bridgeScript = Join-Path $PSScriptRoot "commons_discord_bridge.py"

& $python -B $bridgeScript *> $null
exit $LASTEXITCODE
