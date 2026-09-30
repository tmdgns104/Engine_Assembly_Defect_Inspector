@echo off
setlocal
chcp 65001 >nul
pushd "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  py -3.13 -m venv .venv
  if errorlevel 1 goto failed
)
".venv\Scripts\python.exe" -m pip install -r requirements-capture.txt
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -B -X utf8 -c "import tkinter, cv2, numpy, PIL; from training.capture_windows.misassembly import load_capture_plan; from training.capture_windows.misassembly_app import assets_folder; print('Ready:', len(load_capture_plan(assets_folder() / 'misassembly-plan.json')['steps']), 'capture steps')"
if errorlevel 1 goto failed
echo Ready. Run start_misassembly.cmd or start_capture.cmd.
popd
exit /b 0
:failed
echo Setup failed. Install Python 3.13 x64 with Tcl/Tk and the Python launcher, then retry.
popd
pause
exit /b 1
