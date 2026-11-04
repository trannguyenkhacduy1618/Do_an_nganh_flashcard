


    
  
@echo off
setlocal
cd /d "%~dp0"
title Flashcard App

set "PORT=7909"
set "LAN_IP="

for /f "usebackq delims=" %%I in (`powershell -NoProfile -Command "$ip = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue | Where-Object { $_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.254.*' -and $_.ValidLifetime -ne 0 } | Sort-Object InterfaceMetric | Select-Object -First 1 -ExpandProperty IPAddress; if ($ip) { $ip }"`) do set "LAN_IP=%%I"

cls
echo ============================================
echo          FLASHCARD APP - STARTUP
echo ============================================
echo.
echo Starting main.py...
echo.
if defined LAN_IP (
    echo MOBILE ACCESS:
    echo 1. Connect your phone to the same Wi-Fi as this PC.
    echo 2. Open a browser on your phone.
    echo 3. Enter this address:
    echo.
    echo    http://%LAN_IP%:%PORT%
    echo.
) else (
    echo Could not automatically detect your PC's Wi-Fi IPv4 address.
    echo Run ipconfig and find the IPv4 Address of your Wi-Fi adapter.
    echo Then open this on your phone:
    echo    http://YOUR-PC-IP:%PORT%
    echo.
)
echo Make sure the mobile Flask server in main.py uses:
echo    host="0.0.0.0", port=%PORT%
echo.
echo If the page does not open, allow Python through Windows Firewall
 echo or allow inbound TCP port %PORT%.
echo ============================================
echo.

where py >nul 2>nul
if %errorlevel%==0 (
    py -3 main.py
) else (
    python main.py
)

 echo.
echo The application has stopped.
pause
endlocal