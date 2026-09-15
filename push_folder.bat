@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\push_folder.ps1"
echo.
echo =============================================================
echo Push Folder process finished.
echo =============================================================
pause
endlocal
