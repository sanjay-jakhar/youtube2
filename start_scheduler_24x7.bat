@echo off
title AI YouTube Scheduler - 24/7 Auto Upload
echo.
echo ============================================================
echo   AI Hindi YouTube - 24/7 Scheduler
echo   Uploads automatically at 7:00 AM and 7:30 PM IST
echo   Press Ctrl+C to stop
echo ============================================================
echo.
cd /d "%~dp0"
python main.py --schedule
pause
