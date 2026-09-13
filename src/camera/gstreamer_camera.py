"""One V4L2/GStreamer owner with bounded latest-frame queue and source PTS checks."""

import time
import uuid
from datetime import datetime, timezone

from src.contracts import CameraError, CameraFrame


class GStreamerCamera:
    def __init__(self, config):
        import gi
        import numpy as np
        gi.require_version("Gst", "1.0")
        from gi.repository import Gst
        self.Gst, self.np = Gst, np
        Gst.init(None)
        self.width, self.height = config["width"], config["height"]
        device = config["device"]
        if any(char in device for char in '"\n\r !') or not device.startswith("/dev/"):
            raise CameraError("Invalid camera device path")
        self.pipeline_text = (
            f'v4l2src device="{device}" do-timestamp=false ! '
            f'image/jpeg,width={self.width},height={self.height},framerate={config["fps"]}/1 ! '
            'jpegdec ! videoconvert ! video/x-raw,format=BGR ! '
            'appsink name=frames max-buffers=1 drop=true sync=false')
        self.pipeline = Gst.parse_launch(self.pipeline_text)
        self.sink = self.pipeline.get_by_name("frames")
        self.bus = self.pipeline.get_bus()
        self.sequence = 0
        self.last_pts = -1
        self.epoch = uuid.uuid4().hex
        self.frame_info = {}
        self.open = True
        if self.pipeline.set_state(Gst.State.PLAYING) == Gst.StateChangeReturn.FAILURE:
            self.close()
            raise CameraError("CAMERA_OPEN_FAILED")

    def capture(self):
        Gst = self.Gst
        if not self.open:
            raise CameraError("CAMERA_CLOSED")
        message = self.bus.timed_pop_filtered(0, Gst.MessageType.ERROR | Gst.MessageType.EOS)
        if message:
            self.open = False
            detail = str(message.parse_error()[0]) if message.type == Gst.MessageType.ERROR else "EOS"
            raise CameraError(detail)
        # USB negotiation can exceed the steady-state frame deadline at first open.
        wait = 3000 if self.sequence == 0 else 500
        sample = self.sink.emit("try-pull-sample", wait * Gst.MSECOND)
        if sample is None:
            raise CameraError("CAMERA_FRAME_TIMEOUT")
        buffer = sample.get_buffer()
        caps = sample.get_caps().get_structure(0)
        if (caps.get_value("width"), caps.get_value("height")) != (self.width, self.height):
            raise CameraError("CAPTURE_PROFILE_MISMATCH")
        pts = buffer.pts
        clock = self.pipeline.get_clock()
        if clock is None or pts == Gst.CLOCK_TIME_NONE or pts <= self.last_pts:
            raise CameraError("INVALID_OR_DUPLICATE_CAMERA_PTS")
        age = (clock.get_time() - self.pipeline.get_base_time() - pts) / Gst.SECOND
        if age < -0.1 or age > 1:
            raise CameraError("STALE_CAMERA_PTS")
        success, data = buffer.map(Gst.MapFlags.READ)
        if not success:
            raise CameraError("CAMERA_BUFFER_MAP_FAILED")
        try:
            image = self.np.frombuffer(data.data, dtype=self.np.uint8).reshape(self.height, self.width, 3).copy()
        finally:
            buffer.unmap(data)
        now = time.monotonic()
        self.sequence += 1
        self.last_pts = pts
        self.frame_info = {"sequence": self.sequence, "source_pts_ns": pts,
                           "received_monotonic": now, "estimated_source_monotonic": now - max(age, 0),
                           "age_seconds": max(age, 0), "received_at": datetime.now(timezone.utc).isoformat(),
                           "freshness_method": "v4l2src PTS; appsink drop=true max-buffers=1; increasing PTS; source time after request",
                           "sensor_exposure_timestamp_verified": False}
        return CameraFrame(image, f"{self.epoch}-{self.sequence}", datetime.now(timezone.utc),
                           self.width, self.height, "live")

    def status(self):
        return self.open

    def close(self):
        self.open = False
        self.pipeline.set_state(self.Gst.State.NULL)
