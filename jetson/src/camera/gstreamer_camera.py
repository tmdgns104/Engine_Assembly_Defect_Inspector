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
        gi.require_version('GstVideo', '1.0')
        from gi.repository import GstVideo
        self.GstVideo = GstVideo
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
        self.rejected_frame_info = {}
        self.open = True
        if self.pipeline.set_state(Gst.State.PLAYING) == Gst.StateChangeReturn.FAILURE:
            self.close()
            raise CameraError("CAMERA_OPEN_FAILED")

    def capture(self):
        Gst = self.Gst
        if not self.open:
            raise CameraError("CAMERA_CLOSED")
        message = self.bus.timed_pop_filtered(0, Gst.MessageType.ERROR | Gst.MessageType.EOS | Gst.MessageType.CLOCK_LOST)
        if message:
            self.open = False
            if message.type == Gst.MessageType.CLOCK_LOST:
                self.epoch = uuid.uuid4().hex
                raise CameraError("CAMERA_EPOCH_CHANGED")
            detail = str(message.parse_error()[0]) if message.type == Gst.MessageType.ERROR else "EOS"
            raise CameraError(detail)
        # USB negotiation can exceed the steady-state frame deadline at first open.
        wait = 3000 if self.sequence == 0 else 500
        sample = self.sink.emit("try-pull-sample", wait * Gst.MSECOND)
        if sample is None:
            raise CameraError("CAMERA_FRAME_TIMEOUT")
        buffer = sample.get_buffer()
        if buffer.has_flags(Gst.BufferFlags.CORRUPTED):
            raise CameraError('GSTREAMER_CORRUPTED_BUFFER')
        caps = sample.get_caps().get_structure(0)
        if (caps.get_value("width"), caps.get_value("height")) != (self.width, self.height):
            raise CameraError("CAPTURE_PROFILE_MISMATCH")
        pts = buffer.pts
        self.rejected_frame_info = {'camera_epoch':self.epoch, 'source_pts_ns':pts,
                                    'sequence':self.sequence+1, 'frame_id':f'{self.epoch}-{self.sequence+1}'}
        clock = self.pipeline.get_clock()
        if clock is None or pts == Gst.CLOCK_TIME_NONE:
            raise CameraError("FRAME_METADATA_INVALID")
        if pts < self.last_pts:
            raise CameraError("PTS_REGRESSION")
        if pts == self.last_pts:
            raise CameraError("DUPLICATE_FRAME")
        segment = sample.get_segment()
        if segment is None or segment.format != Gst.Format.TIME or segment.rate != 1.0:
            raise CameraError("FRAME_METADATA_INVALID")
        running_pts = segment.to_running_time(Gst.Format.TIME, pts)
        if running_pts == Gst.CLOCK_TIME_NONE:
            raise CameraError("FRAME_METADATA_INVALID")
        # Anchor before reading GstClock, not after the potentially slow image copy.
        # This conservative mapping avoids making an old frame appear newer.
        anchor = time.monotonic()
        clock_now = clock.get_time()
        anchor_end = time.monotonic()
        age = (clock_now - self.pipeline.get_base_time() - running_pts) / Gst.SECOND
        if age < 0 or age > 1:
            raise CameraError("FRAME_METADATA_INVALID" if age < 0 else "STALE")
        estimated_source = anchor - max(age, 0)
        success, data = buffer.map(Gst.MapFlags.READ)
        if not success:
            raise CameraError("CAMERA_BUFFER_MAP_FAILED")
        try:
            video_info = self.GstVideo.VideoInfo.new_from_caps(sample.get_caps())
            stride, offset = video_info.stride[0], video_info.offset[0]
            if stride < self.width*3 or len(data.data) < offset+(self.height-1)*stride+self.width*3:
                raise CameraError('CAMERA_BUFFER_STRIDE_INVALID')
            image = self.np.ndarray((self.height,self.width,3), dtype=self.np.uint8,
                                   buffer=data.data, offset=offset, strides=(stride,3,1)).copy()
        finally:
            buffer.unmap(data)
        now = time.monotonic()
        self.sequence += 1
        self.last_pts = pts
        frame_id = f"{self.epoch}-{self.sequence}"
        self.frame_info = {"frame_id": frame_id, "camera_epoch": self.epoch,
                           "sequence": self.sequence, "source_pts_ns": pts, "source_running_time_ns": running_pts,
                           "received_monotonic": now, "estimated_source_monotonic": estimated_source,
                           "clock_mapping_uncertainty_ms": (anchor_end-anchor)*1000,
                           "age_seconds": now-estimated_source, "received_at": datetime.now(timezone.utc).isoformat(),
                           "freshness_method": "v4l2src PTS + segment running-time mapped to local monotonic; exposure unverified",
                           "sensor_exposure_timestamp_verified": False}
        self.frame_info.update(width=self.width,height=self.height,stride_bytes=stride,
                               coordinate_space='image_pixels',pixel_format='BGR8')
        self.rejected_frame_info = {}
        return CameraFrame(image, frame_id, datetime.now(timezone.utc),
                           self.width, self.height, "live")

    def status(self):
        return self.open

    def close(self):
        self.open = False
        self.pipeline.set_state(self.Gst.State.NULL)
