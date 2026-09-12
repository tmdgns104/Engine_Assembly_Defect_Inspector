@echo off
setlocal
chcp 65001 >nul
set "CAPTURE_PROJECT=%~dp0.."
if not exist "%CAPTURE_PROJECT%\.venv\Scripts\python.exe" (
  echo [ERROR] Project Python not found: "%CAPTURE_PROJECT%\.venv\Scripts\python.exe"
  echo Existing project .venv is required. No packages were installed.
  pause
  exit /b 1
)
pushd "%CAPTURE_PROJECT%"
if errorlevel 1 exit /b 1
"%CAPTURE_PROJECT%\.venv\Scripts\python.exe" -X utf8 -m training.capture_windows %*
set "CAPTURE_EXIT=%ERRORLEVEL%"
popd
if not "%CAPTURE_EXIT%"=="0" (
  echo.
  echo Capture program failed. Exit code: %CAPTURE_EXIT%
  pause
)
exit /b %CAPTURE_EXIT%
