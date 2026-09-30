"""Frozen entry: dispatch camera subprocesses before importing Tk or OpenCV UI."""
import multiprocessing
import os
from pathlib import Path
import sys
import traceback

from training.capture_windows.portable import (ensure_standard_streams,
                                               show_startup_error, camera_diagnostic_stage)


def camera_diagnostic_log():
    """Opt-in local startup evidence, inherited by this check's camera worker."""
    if len(sys.argv) == 4 and sys.argv[1] == '--camera-check':
        destination = Path(sys.argv[2]).resolve()
        os.environ['ENGINE_CAPTURE_CAMERA_CHECK_LOG'] = str(destination.with_name(destination.name + '-worker-logs'))
    directory = os.environ.get('ENGINE_CAPTURE_CAMERA_CHECK_LOG')
    if not directory:
        return
    folder = Path(directory)
    folder.mkdir(parents=True, exist_ok=True)
    stream = (folder / f'process-{os.getpid()}.log').open('a', encoding='utf-8', buffering=1)
    sys.stderr = stream
    camera_diagnostic_stage('entry: ' + repr(sys.argv))


def main():
    ensure_standard_streams()
    camera_diagnostic_log()
    camera_diagnostic_stage('before freeze_support')
    multiprocessing.freeze_support()
    camera_diagnostic_stage('after freeze_support')
    if len(sys.argv) == 4 and sys.argv[1] == '--camera-check':
        return run_diagnostic(sys.argv[1], Path(sys.argv[2]), int(sys.argv[3]))
    if len(sys.argv) == 3 and sys.argv[1] == '--ui-self-test':
        return run_diagnostic(sys.argv[1], Path(sys.argv[2]))
    if len(sys.argv) == 3 and sys.argv[1] == '--self-test':
        return run_diagnostic(sys.argv[1], Path(sys.argv[2]))
    if len(sys.argv) != 1:
        return 2
    try:
        import tkinter as tk
        from training.capture_windows.misassembly_app import MisassemblyApp
        root = tk.Tk()
        MisassemblyApp(root)
        root.mainloop()
        return 0
    except Exception:
        log_root = Path(sys.executable).resolve().parent / 'logs'
        log_root.mkdir(exist_ok=True)
        log = log_root / 'startup-error.txt'
        log.write_text(traceback.format_exc(), encoding='utf-8')
        show_startup_error(f'오조립 촬영기를 시작하지 못했습니다. 오류 기록: {log}')
        return 1


def run_diagnostic(mode, destination, index=None):
    """Developer failures go to evidence and an exit code, never a modal popup."""
    try:
        if mode == '--camera-check':
            from training.capture_windows.misassembly_ui_selftest import run_camera
            camera_diagnostic_stage('camera UI imports ready')
            return run_camera(destination, index)
        if mode == '--ui-self-test':
            from training.capture_windows.misassembly_ui_selftest import run
        else:
            from training.capture_windows.misassembly_selftest import run
        return run(destination)
    except Exception:
        destination.mkdir(parents=True, exist_ok=True)
        (destination/'entry-error.txt').write_text(traceback.format_exc(), encoding='utf-8')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
