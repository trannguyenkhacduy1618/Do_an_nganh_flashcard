
@echo off
setlocal
title Flashcard App - Install Requirements

cd /d "%~dp0"

echo =====================================
echo     Flashcard App Requirements
echo =====================================
echo.

REM Check Python
where py >nul 2>nul
if %errorlevel%==0 (
    set "PY=py"
) else (
    where python >nul 2>nul
    if %errorlevel% neq 0 (
        echo [ERROR] Python is not installed or not in PATH.
        pause
        exit /b 1
    )
    set "PY=python"
)

REM Check requirements.txt
if not exist requirements.txt (
    echo [ERROR] requirements.txt not found!
    pause
    exit /b 1
)

echo Checking pip...
%PY% -m pip --version
if errorlevel 1 (
    echo [ERROR] pip is unavailable.
    pause
    exit /b 1
)

echo.
echo Installing requirements...
%PY% -m pip install -r requirements.txt

if errorlevel 1 (
    echo.
    echo [ERROR] Installation failed.
    pause
    exit /b 1
)

echo.
echo All requirements installed successfully!
echo You can now run Run_Flashcard_App.bat
pause
