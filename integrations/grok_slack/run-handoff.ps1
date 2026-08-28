$ErrorActionPreference = "Stop"
# Local browser activation. Tokens are pasted in the loopback page, never here.
$python = (Get-Command python -ErrorAction Stop).Source
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
& $python "$here\handoff.py" serve --open-browser @args
exit $LASTEXITCODE
