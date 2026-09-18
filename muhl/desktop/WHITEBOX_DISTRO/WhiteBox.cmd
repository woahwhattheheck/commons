@echo off
REM White Box - the main instrument (http://127.0.0.1:7862). Set WHITEBOX_MODELS_DIR here if you prefer it to the config file.
cd /d "%~dp0"
python whitebox_app.py %*
pause
