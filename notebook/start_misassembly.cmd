@echo off
setlocal
chcp 65001 >nul
set "CAPTURE_PYTHON=%~dp0.venv\Scripts\python.exe"
if not exist "%CAPTURE_PYTHON%" (
  echo Run setup_capture.cmd first.
  pause
  exit /b 1
)
pushd "%~dp0"
"%CAPTURE_PYTHON%" -B -X utf8 -m training.capture_windows.misassembly_entry %*
set "CAPTURE_EXIT=%ERRORLEVEL%"
popd
if not "%CAPTURE_EXIT%"=="0" pause
exit /b %CAPTURE_EXIT%
