"""Run with the project venv: python -m training.capture_windows."""
import argparse
import multiprocessing
from pathlib import Path
import sys


def main(argv=None):
    parser = argparse.ArgumentParser(description='제품 설정 기반 Windows 데이터 촬영 화면')
    parser.add_argument('--profile', type=Path)
    parser.add_argument('--output-root', type=Path)
    parser.add_argument('--manual', action='store_true', help='기존 수동 / 한 조건 촬영 화면')
    args = parser.parse_args(argv)
    root = None
    try:
        import tkinter as tk
        from .app import CaptureApp, DEFAULT_PROFILE
        from .wizard_app import WizardApp
        root = tk.Tk()
        app = (CaptureApp if args.manual else WizardApp)(root, args.profile or DEFAULT_PROFILE, args.output_root)
        root.mainloop()
        if not args.manual and app.manual_requested:
            import gc
            del app, root
            gc.collect()  # old Tk interpreter finalizers belong on this thread
            root = tk.Tk()
            CaptureApp(root, args.profile or DEFAULT_PROFILE, args.output_root)
            root.mainloop()
        return 0
    except Exception as exc:
        print(f'촬영 화면 실행 실패: {exc}', file=sys.stderr)
        print('프로젝트 .venv의 Python / OpenCV / Pillow / Tkinter를 확인하세요.', file=sys.stderr)
        if root is not None:
            root.destroy()
        return 1


if __name__ == '__main__':
    multiprocessing.freeze_support()
    raise SystemExit(main())
