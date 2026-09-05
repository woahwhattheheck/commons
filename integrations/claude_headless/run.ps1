$ErrorActionPreference = "Stop"

# Start the headless Claude gateway as a console-free background process on
# 127.0.0.1:8879 and print its health line. Idempotent: if it is already
# answering, the existing process is reported instead of a second one.
$python = (Get-Command python -ErrorAction Stop).Source
& $python "$PSScriptRoot\gateway.py" --detach @args
exit $LASTEXITCODE
