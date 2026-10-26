@echo off
REM ============================================================
REM  Cai dat protocol "flashcard://" de extension mo duoc App
REM  Chi can chay 1 lan. Khong can quyen Administrator.
REM ============================================================
setlocal
cd /d "%~dp0"

where python >nul 2>nul
if %errorlevel%==0 (
    python install_protocol.py %*
) else (
    py install_protocol.py %*
)

echo.
pause
endlocal
