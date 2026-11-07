@echo off
setlocal
cd /d "%~dp0"
title Flashcard App

set "PORT=7909"
set "LAN_IP="

for /f "usebackq delims=" %%I in (`powershell -NoProfile -Command "$ip = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue | Where-Object { $_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.254.*' -and $_.ValidLifetime -ne 0 } | Sort-Object InterfaceMetric | Select-Object -First 1 -ExpandProperty IPAddress; if ($ip) { $ip }"`) do set "LAN_IP=%%I"
where py >nul 2>nul
if %errorlevel%==0 (
    py -3 main.py
) else (
    python main.py
)
cls
echo ============================================
echo          FLASHCARD APP - STARTUP
echo ============================================
echo.
echo Starting main.py...
echo.



exit