@echo off
setlocal
chcp 65001 >nul
set "CAPTURE_ROOT=%~dp0"
set "CAPTURE_PYTHON=%CAPTURE_ROOT%.venv\Scripts\python.exe"
if not exist "%CAPTURE_PYTHON%" set "CAPTURE_PYTHON=%CAPTURE_ROOT%..\.venv\Scripts\python.exe"
if not exist "%CAPTURE_PYTHON%" (
  echo [ERROR] Create the notebook Python environment described in README.md first.
  pause
  exit /b 1
)
pushd "%CAPTURE_ROOT%"
"%CAPTURE_PYTHON%" -B -X utf8 -m training.capture_windows --profile training/datasets/engine/engine_model_top_v0/profile.json --output-root data/engine/raw %*
set "CAPTURE_EXIT=%ERRORLEVEL%"
popd
if not "%CAPTURE_EXIT%"=="0" pause
exit /b %CAPTURE_EXIT%
