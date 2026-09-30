"""Portable packaging boundary: bundled inputs, persistent outputs beside the EXE."""
from datetime import datetime
import os
from pathlib import Path
import sys
import traceback


ENGINE_PROFILE = Path('training/datasets/engine/engine_model_top_v0/profile.json')


def locations():
    """Separate onefile's temporary resources from the user's persistent data."""
    if getattr(sys, 'frozen', False):
        resources = Path(sys._MEIPASS)
        home = Path(sys.executable).resolve().parent
    else:
        resources = home = Path(__file__).resolve().parents[2]
    return resources / ENGINE_PROFILE, home / 'data/engine/raw', home / 'logs'


def ensure_standard_streams():
    # Windowed Python has None streams; spawned workers also need valid streams.
    for name in ('stdout', 'stderr'):
        if getattr(sys, name) is None:
            setattr(sys, name, open(os.devnull, 'w', encoding='utf-8'))


def camera_diagnostic_stage(stage):
    """Local opt-in startup timings; never writes images or enables a camera."""
    directory = os.environ.get('ENGINE_CAPTURE_CAMERA_CHECK_LOG')
    if not directory:
        return
    from datetime import timezone
    folder = Path(directory)
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / f'process-{os.getpid()}.log').open('a', encoding='utf-8') as stream:
        stream.write(f'{datetime.now(timezone.utc).isoformat()} {stage}\n')


def show_startup_error(message):
    # A native dialog still works when Tcl/Tk itself cannot initialize.
    if sys.platform == 'win32':
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, message, 'Engine Dataset Wizard', 0x10)
    else:
        print(message, file=sys.stderr)


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    profile, output, logs = locations()
    if len(args) == 2 and args[0] == '--self-test':
        from .portable_check import run_check
        return run_check(profile, output, Path(args[1]).absolute())
    if args:
        show_startup_error('실행 파일을 더블클릭해 시작하세요. 지원하지 않는 실행 인자가 있습니다.')
        return 2
    try:
        logs.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        log_path = logs / f'startup_{stamp}_{os.getpid()}.log'
        with log_path.open('x', encoding='utf-8', buffering=1) as stream:
            previous = sys.stdout, sys.stderr
            sys.stdout = sys.stderr = stream
            try:
                # Same entry point as the existing .cmd launcher, with explicit paths.
                from .__main__ import main as run_wizard
                result = run_wizard(['--profile', str(profile), '--output-root', str(output)])
            except Exception:
                traceback.print_exc()
                result = 1
            finally:
                sys.stdout, sys.stderr = previous
        if result:
            show_startup_error(f'프로그램을 시작하지 못했습니다.\n오류 기록: {log_path}\n'
                               'ZIP 전체를 쓰기 가능한 폴더에 압축 해제한 뒤 다시 실행하세요.')
        return result
    except OSError as error:
        show_startup_error('실행 폴더에 기록을 저장할 수 없습니다.\n'
                           '바탕 화면이나 문서처럼 쓰기 가능한 폴더에 압축을 풀어 실행하세요.\n'
                           f'{error}')
        return 1
