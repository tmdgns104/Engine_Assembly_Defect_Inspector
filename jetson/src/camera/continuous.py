"""Worker 안의 단일 수신 소유자. 최신 프레임 하나만 보존하여 대기열 지연을 제한한다."""
import threading
import time
from src.contracts import CameraError
from src.camera.frame_integrity import inspect_integrity


class ContinuousFrames:
    def __init__(self, camera, stopping, on_frame):
        self.camera, self.stopping, self.on_frame = camera, stopping, on_frame
        self.pipeline_text = camera.pipeline_text
        self.condition = threading.Condition()
        self.local_stop = threading.Event()
        self.latest = None
        self.consumed = None
        self.error = None
        self.frame_info = {}
        self.rejected_frame_info = {}
        self.closed = False
        self.thread = threading.Thread(target=self._receive, name='single-camera-receiver', daemon=True)
        self.thread.start()

    def _receive(self):
        try:
            while not self.stopping.is_set() and not self.local_stop.is_set():
                frame = self.camera.capture()
                metadata = dict(self.camera.frame_info)
                metadata['integrity'] = inspect_integrity(frame.image)
                frame.image.setflags(write=False)
                self.on_frame(frame, metadata)
                with self.condition:
                    self.latest = (frame, metadata)
                    self.condition.notify_all()
        except Exception as error:
            with self.condition:
                self.error = error
                self.condition.notify_all()
        finally:
            # 생성 이후의 Camera.close 소유권은 수신 thread에만 있다.
            self.camera.close()

    def capture(self):
        deadline = time.monotonic() + 4
        with self.condition:
            while True:
                if self.error:
                    raise CameraError('CONTINUOUS_CAPTURE_FAILED: ' + str(self.error)) from self.error
                if self.local_stop.is_set() or self.stopping.is_set():
                    raise CameraError('CAMERA_CLOSED')
                if self.latest is not None and self.latest[0].frame_id != self.consumed:
                    frame, metadata = self.latest
                    self.consumed = frame.frame_id
                    self.frame_info = dict(metadata)
                    self.frame_info['age_seconds'] = time.monotonic()-metadata['estimated_source_monotonic']
                    return frame
                remaining = deadline-time.monotonic()
                if remaining <= 0:
                    raise CameraError('CONTINUOUS_FRAME_TIMEOUT')
                self.condition.wait(min(.1, remaining))

    def close(self):
        if self.closed:
            return
        self.local_stop.set()
        with self.condition:
            self.condition.notify_all()
        self.thread.join(4)
        if self.thread.is_alive():
            raise RuntimeError('CAMERA_RECEIVER_SHUTDOWN_UNCONFIRMED')
        self.closed = True
