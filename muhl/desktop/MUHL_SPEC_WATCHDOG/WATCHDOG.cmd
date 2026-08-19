@echo off
title MUHL SPEC WATCHDOG - staring at Claude
cd /d "%~dp0"
echo Starting the spec watchdog in ENFORCE mode. Leave this window open.
echo It will scream and kill Claude the instant it hedges/doubts/judges/interprets.
echo.
python muhl_spec_watchdog.py --enforce --beep
pause
