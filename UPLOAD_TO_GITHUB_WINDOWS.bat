@echo off
setlocal
cd /d "%~dp0"
title PCLQ GitHub Uploader
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\upload_to_github.ps1"
set EXITCODE=%ERRORLEVEL%
echo.
if not "%EXITCODE%"=="0" (
  echo UPLOAD FAILED. Read the error shown above.
) else (
  echo GitHub upload completed.
)
pause
exit /b %EXITCODE%
