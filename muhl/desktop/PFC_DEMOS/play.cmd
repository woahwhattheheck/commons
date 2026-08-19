@echo off
REM pfc demos launcher — double-click, pick a demo. Runs from the repo's host/ folder.
cd /d "%~dp0..\LocalDeviceAgent"
:menu
echo.
echo   ======  RUNNING ON THE pfc  ======
echo   1  Tetris        (arrows / WASD)
echo   2  Raycaster 3D  (WASD)
echo   3  Tunnel        (sit back)
echo   4  Game of Life  (click to seed)
echo   5  Brian's Brain
echo   6  Operator      (neural forward pass on the pfc)
echo   0  Quit
echo.
set /p c=Pick a number:
if "%c%"=="1" python host\pfc_tetris.py
if "%c%"=="2" python host\pfc_raycast.py
if "%c%"=="3" python host\pfc_tunnel.py
if "%c%"=="4" python host\pfc_game.py life
if "%c%"=="5" python host\pfc_game.py brain
if "%c%"=="6" python host\pfc_operator.py
if "%c%"=="0" exit
goto menu
