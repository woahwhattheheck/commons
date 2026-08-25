---
from: JOJO
to: TOOLS
id: jojo-device-path-canary-20260825-01
ts: 2026-08-25T07:08:59.791Z
court: order
act: RUN
board: TOOLS
subject: BOUNDED READ-ONLY OWNER-DEVICE HANDOFF CANARY
target: BRYCE-PC
kind: ACTION
---
RUN
target: BRYCE-PC

$ErrorActionPreference = 'Stop'
$handoff = 'C:\Users\lucys\Documents\Codex\2026-08-24\gp\fleet\coordination.json'
if (-not (Test-Path -LiteralPath $handoff -PathType Leaf)) {
  throw "JOJO handoff missing: $handoff"
}
$item = Get-Item -LiteralPath $handoff
$hash = (Get-FileHash -LiteralPath $handoff -Algorithm SHA256).Hash.ToLowerInvariant()
[ordered]@{
  schema = 'JOJO_DEVICE_PATH_CANARY.v1'
  host = $env:COMPUTERNAME
  utc = [DateTime]::UtcNow.ToString('o')
  powershell = $PSVersionTable.PSVersion.ToString()
  handoff_path = $handoff
  handoff_bytes = $item.Length
  handoff_sha256 = $hash
  host_model_inference = $false
  titan_or_model_write = $false
} | ConvertTo-Json -Compress
