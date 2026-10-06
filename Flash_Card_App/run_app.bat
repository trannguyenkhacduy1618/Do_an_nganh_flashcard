@echo off
REM ============================================================
REM  Chay Flash Card App (Tkinter) + cau noi HTTP o cong 5000
REM  Duoc goi tu nut "Mo App" tren Browser Extension (flashcard://)
REM ============================================================
setlocal

REM Di chuyen ve dung thu muc Flash_Card_App de cac import hoat dong
cd /d "%~dp0"

REM Uu tien Python Launcher 'py' (on dinh hon, tranh alias Microsoft Store),
REM neu khong co thi dung 'python'.
where py >nul 2>nul
if %errorlevel%==0 (
    py main.py
) else (
    python main.py
)

REM Neu muon AN cua so console, doi 'main.py' thanh 'pythonw main.py'
endlocal
