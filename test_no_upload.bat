@echo off
title AI YouTube - Test (No Upload)
echo.
echo ============================================================
echo   AI Hindi YouTube - Test Mode (Video Only, No Upload)
echo ============================================================
echo.
cd /d "%~dp0"
python main.py --test --genre horror
echo.
pause
