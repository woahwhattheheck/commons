@echo off
REM ========================================================================
REM  SDC WHITE-BOX LOOP (browser UI).  Double-click to run.
REM
REM  The closed aimed loop: a small model's forward pass (y = W . x) is a
REM  VERIFIED circuit stored INSIDE titan.gguf; the weights are stored data.
REM  The White Box READS each run and AIMS each weight edit - directed, not
REM  blind - projecting the error through the weight tensor (do_direction's
REM  move) to pick the responsible weight, then re-reading the run to confirm
REM  the edit helped. The block converges to the target on power, ~0 RAM.
REM
REM  This is the stepping stone: the White Box still runs on the host here.
REM  Next, the reader itself becomes stored gates and reads the run natively.
REM
REM  A dashboard opens at http://127.0.0.1:7998 with Step / Run-to-target /
REM  Reset, the live weight grid, y-vs-target, and the error curve. Close
REM  this window or Ctrl-C to stop (nothing lingers; 0 background process).
REM ========================================================================
title SDC White-Box Loop (run, read, aim the edit)
cd /d "%~dp0"
set PY=%LOCALAPPDATA%\Programs\Python\Python312\python.exe
if not exist "%PY%" set PY=python
echo Starting the SDC White-Box Loop UI... a browser will open at http://127.0.0.1:7998
echo Leave this window open; close it to end.
echo.
"%PY%" "%~dp0sdc_whitebox_train.py" --ui
echo.
pause
