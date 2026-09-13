"""Bounded camera timestamp check, without detection or inspection approval."""

import json
from pathlib import Path
from src.camera.gstreamer_camera import GStreamerCamera

config = json.loads(Path("config/earbud_bench.json").read_text())
camera = GStreamerCamera(config["camera"])
observations = []
try:
    for index in range(12):
        frame = camera.capture()
        observations.append(dict(camera.frame_info, width=frame.width, height=frame.height))
finally:
    camera.close()
print(json.dumps(observations, indent=2))
