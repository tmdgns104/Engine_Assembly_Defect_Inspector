"""Explicit synthetic GUI fixture. No USB access; outputs only under runs/.

Run from project root with the project Python and this file. --review opens a
pending comparison. Simulated declarations here are test fixtures, not human
or physical-device evidence. Production launchers never import this module.
"""
import argparse
from dataclasses import replace
from pathlib import Path
import sys
import time
import tkinter as tk

import cv2
import numpy as np

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))
from training.capture_windows.wizard import Collection
from training.capture_windows.wizard_app import WizardApp
from test_dataset_wizard_ui import WizardCamera


class VisualCamera(WizardCamera):
    def poll(self):
        super().poll()
        if self.latest is None:
            return
        image = np.full((720, 1280, 3), (64, 57, 49), np.uint8)
        cv2.rectangle(image, (440, 270), (840, 470), (180, 190, 200), -1)
        if self.seed not in (3, 5):
            cv2.circle(image, (540, 365), 44, (70, 135, 240), -1)
        if self.seed not in (4, 5):
            cv2.circle(image, (730, 365), 44, (220, 155, 65), -1)
        cv2.putText(image, 'SYNTHETIC UI TEST / NO CAMERA', (260, 150), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (230, 230, 230), 2)
        self.latest.image = image
        self.latest.camera.update(width=1280, height=720, requested_width=1280, requested_height=720)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--review', action='store_true')
    args = parser.parse_args()
    root = tk.Tk()
    camera = VisualCamera()
    app = WizardApp(root, output_root=PROJECT/'runs/dataset-wizard-001/visual-sample', camera=camera)
    camera.connect()
    col = Collection.create(app.output_root, app.profile, app.guide, app.plan, True, 'sample')
    col.new_setup(camera.snapshot(), [.34, .37, .32, .29], 'screen_left_is_physical_left')
    app.collection, app.roi = col, [.34, .37, .32, .29]
    app.paused, app.resume_verified = False, True
    if args.review:
        for i in range(6):
            camera.seed = i if i < 2 else i
            ticket = col.prepare(camera.snapshot(), now=time.monotonic()-2)
            a = col.save_prepared(ticket, camera.snapshot())
            if a['metrics']['warnings']:
                col.acknowledge_quality(a['attempt_id'], True)
            if i == 1:
                col.confirm_setup(True)  # simulated setup fixture only
    root.title('수집 길잡이 · SYNTHETIC UI TEST · 실제 카메라 사용 없음')
    app.refresh()
    root.mainloop()


if __name__ == '__main__':
    main()
