"""One owner for camera open/read/release; the Tk thread never calls a driver.

Each connection gets fresh queues and a stream ID. Only an explicitly selected
index/backend is opened. A blocked native call can be ended by terminating our
own disposable process, never another app's camera process.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
import math
import multiprocessing as mp
from queue import Empty, Full
import time
import uuid

import cv2
import numpy as np

BACKENDS = {"DSHOW": cv2.CAP_DSHOW, "MSMF": cv2.CAP_MSMF}
MAX_FRAME_AGE = 1.0


@dataclass(frozen=True)
class CameraSettings:
    index: int
    backend: str
    width: int
    height: int

    def __post_init__(self):
        if type(self.index) is not int or not 0 <= self.index <= 99:
            raise ValueError("카메라 후보 인덱스는 0~99 정수입니다.")
        if self.backend not in BACKENDS:
            raise ValueError("DSHOW 또는 MSMF를 선택하세요.")
        if any(type(n) is not int or not 1 <= n <= 8192 for n in (self.width, self.height)):
            raise ValueError("유효한 요청 해상도를 선택하세요.")

    @property
    def source(self):
        return f"windows:{self.backend}:index={self.index}"


@dataclass
class Frame:
    image: np.ndarray
    captured_at: datetime
    received_mono: float
    sequence: int
    stream_id: str
    camera: dict

    def fresh(self, now=None):
        age = (time.monotonic() if now is None else now) - self.received_mono
        return 0 <= age <= MAX_FRAME_AGE


def reported_number(cap, prop):
    try:
        value = float(cap.get(prop))
        return value if math.isfinite(value) and value > 0 else None
    except (cv2.error, ValueError, TypeError):
        return None


def camera_details(cap, settings, image):
    backend = cap.getBackendName()
    if backend != settings.backend:
        raise RuntimeError(f"요청 backend {settings.backend}, 실제 {backend}: 연결을 중단합니다.")
    code = reported_number(cap, cv2.CAP_PROP_FOURCC)
    fourcc = None
    if code is not None and code <= 0xFFFFFFFF:
        candidate = ''.join(chr((int(code) >> (8*i)) & 255) for i in range(4))
        if all(32 <= ord(c) <= 126 for c in candidate):
            fourcc = candidate
    h, w = image.shape[:2]
    return {"index": settings.index, "backend": backend,
            "device_name": None, "requested_width": settings.width,
            "requested_height": settings.height, "width": w, "height": h,
            "fps_reported": reported_number(cap, cv2.CAP_PROP_FPS),
            "fourcc_reported": fourcc}


def capture_loop(settings, stream_id, stop, frames, events, factory=None):
    """factory is a test seam; production always uses cv2.VideoCapture."""
    cap = None
    try:
        cap = (factory or cv2.VideoCapture)()
        if not cap.open(settings.index, BACKENDS[settings.backend]):
            raise RuntimeError("연결 실패. 선택한 후보·backend·Windows 권한·다른 앱 점유를 확인하세요.")
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, settings.width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, settings.height)
        sequence = 0
        while not stop.is_set():
            ok, image = cap.read()
            if stop.is_set():
                break
            if not ok or image is None or image.size == 0:
                raise RuntimeError("영상 읽기 실패. 연결이 끊겼거나 장치가 응답하지 않습니다.")
            if image.dtype != np.uint8 or image.ndim != 3 or image.shape[2] != 3:
                raise RuntimeError("8-bit BGR 프레임이 아닙니다. 다른 backend/설정을 확인하세요.")
            # Software receive time, not a sensor exposure timestamp.
            stamp, mono = datetime.now(timezone.utc), time.monotonic()
            sequence += 1
            frame = Frame(image.copy(), stamp, mono, sequence, stream_id,
                          camera_details(cap, settings, image))
            try:
                frames.put_nowait(frame)
            except Full:
                # Remove queued preview only; dataset capture is never automatic.
                try:
                    frames.get_nowait()
                except Empty:
                    pass
                try:
                    frames.put_nowait(frame)
                except Full:
                    pass
            stop.wait(0.005)
    except Exception as exc:
        events.put(("error", str(exc)))
    finally:
        if cap is not None:
            cap.release()


def camera_process(settings, stream_id, stop, frames, events):
    # Preview messages may be discarded on exit; no dataset is written here.
    frames.cancel_join_thread()
    capture_loop(settings, stream_id, stop, frames, events)


class CameraClient:
    source_kind = 'camera'

    def __init__(self, context=None, target=camera_process):
        self.context = context or mp.get_context("spawn")
        self.target = target
        self.process = None
        self.latest = None
        self.state = "disconnected"
        self.error = ""
        self.settings = None
        self.deadline = None

    def connect(self, settings):
        if self.process is not None:
            raise RuntimeError("기존 카메라 해제가 끝난 뒤 다시 연결하세요.")
        self.settings = settings
        self.stream_id = uuid.uuid4().hex
        self.frames = self.context.Queue(maxsize=1)
        self.events = self.context.Queue()
        self.stop = self.context.Event()
        self.latest, self.error, self.deadline = None, "", None
        self.state = "connecting"
        self.started = time.monotonic()
        self.process = self.context.Process(target=self.target,
            args=(settings, self.stream_id, self.stop, self.frames, self.events), daemon=True)
        try:
            self.process.start()
        except Exception:
            self.process = None
            self.frames.close()
            self.events.close()
            self.state = "error"
            raise

    def disconnect(self):
        self.latest = None
        if self.process is not None and self.deadline is None:
            self.stop.set()
            self.deadline = time.monotonic() + 2.0
            self.state = "stopping"

    def poll(self):
        if self.process is None:
            return
        while True:
            try:
                _, self.error = self.events.get_nowait()
                self.disconnect()
            except Empty:
                break
        # Bound the work per UI tick even if a producer is very fast.
        for _ in range(2):
            try:
                packet = self.frames.get_nowait()
                if self.deadline is None and packet.stream_id == self.stream_id:
                    self.latest = packet
                    self.state = "connected"
            except Empty:
                break
        now = time.monotonic()
        if self.state == "connecting" and now-self.started > 15:
            self.error = "연결 시간 초과. 후보와 backend를 확인하세요. 자동 대체하지 않습니다."
            self.disconnect()
        if self.deadline is not None and now >= self.deadline and self.process.is_alive():
            self.process.terminate()
            self.error = self.error or "장치 응답 지연으로 이 앱의 카메라 작업을 종료했습니다."
        if not self.process.is_alive():
            unexpected = self.deadline is None
            self.process.join(timeout=0)
            self.process.close()
            self.process = None
            self.frames.close()
            self.events.close()
            self.latest = None
            if unexpected and not self.error:
                self.error = "카메라 작업이 종료되었습니다. 다시 연결하세요."
            self.state = "error" if self.error else "disconnected"

    def snapshot(self):
        self.poll()
        if self.state != "connected" or self.latest is None or not self.latest.fresh():
            raise RuntimeError("정상 수신 중인 최신 프레임이 없습니다. 저장하지 않았습니다.")
        frame = self.latest
        return Frame(frame.image.copy(), frame.captured_at, frame.received_mono,
                     frame.sequence, frame.stream_id, dict(frame.camera))
