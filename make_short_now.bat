@echo off
title AI YouTube - Make Short Video Now
echo.
echo ============================================================
echo   AI Hindi YouTube - Make YouTube SHORT (under 60s, 9:16)
echo ============================================================
echo.
cd /d "%~dp0"
python main.py --shorts --genre horror
echo.
pause
