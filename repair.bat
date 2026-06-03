@echo off
title Wire0 Repair
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0repair.ps1"
echo.
pause
