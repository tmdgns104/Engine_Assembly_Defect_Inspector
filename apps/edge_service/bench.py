"""Jetson-only BENCH: one camera/model worker, responsive local HTTP, request-only evidence."""

import argparse
import hashlib
import json
import os
import platform
import signal
import threading
import time
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from src.decision.bench import calibrate, decide


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def atomic_write(path, data):
    """Write once, flush bytes and directory; never replace a previous evidence file."""
    if path.exists():
        raise FileExistsError(path)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("xb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    os.rename(temporary, path)
    if os.name == "posix":
        descriptor = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)


class BusyError(RuntimeError):
    pass


class BenchWorker(threading.Thread):
    def __init__(self, config, config_bytes, model_path, output, camera_factory=None, detector_factory=None):
        super().__init__(daemon=True, name="camera-model-owner")
        self.config, self.config_hash = config, digest(config_bytes)
        self.model_path, self.output = model_path, output
        self.camera_factory, self.detector_factory = camera_factory, detector_factory
        self.lock, self.stopping = threading.Lock(), threading.Event()
        self.state, self.error = "INITIALIZING", None
        self.job = None
        self.preview, self.last_overlay = None, None
        self.last_frame_time = 0
        self.last_result, self.calibration, self.candidate = None, None, None
        self.backend = {"backend": "pytorch", "device": "UNVERIFIED", "hostname": platform.node()}
        self.output.mkdir(parents=True, exist_ok=True)

    def snapshot(self):
        with self.lock:
            age = time.monotonic() - self.last_frame_time if self.last_frame_time else None
            expired = self.job and time.monotonic() > self.job["deadline"]
            return {"state": "ERROR" if expired else self.state,
                    "error": "INSPECTION_TIMEOUT; worker completion pending" if expired else self.error,
                    "preview_age_seconds": age, "camera_current": age is not None and age < 2 and self.state != "ERROR",
                    "backend": self.backend, "model_sha256": self.config["model_sha256"],
                    "config_sha256": self.config_hash, "product_id": self.config["product_id"],
                    "last_result": self.last_result, "calibration_confirmed": bool(self.calibration),
                    "calibration_candidate": self.candidate,
                    "limitations": self.config["limitations"], "source": "live", "mode": "BENCH_EDGE"}

    def submit(self, kind, visibility):
        if visibility is not True:
            raise ValueError("촬영 조건 확인이 필요합니다.")
        with self.lock:
            if self.job is not None or self.state == "BUSY":
                raise BusyError("BUSY")
            if self.state != "READY" or time.monotonic() - self.last_frame_time > 2:
                raise ValueError("카메라/모델이 준비되지 않았습니다.")
            if kind == "inspect" and not self.calibration:
                raise ValueError("정상 기준 자리 확인이 필요합니다.")
            now = time.monotonic()
            job = {"request_id": uuid.uuid4().hex, "kind": kind, "requested_at": utc_now(),
                   "accepted_monotonic": now, "deadline": now + self.config["inspection_timeout_seconds"],
                   "visibility_confirmed": visibility}
            directory = self.output / job["request_id"]
            try:
                directory.mkdir(exist_ok=False)
                atomic_write(directory / "request.json", json.dumps(job, ensure_ascii=False).encode())
            except OSError:
                self.state, self.error = "ERROR", "PERSISTENCE_ERROR"
                raise
            self.job, self.state = job, "BUSY"
            return job["request_id"]

    def confirm_calibration(self, candidate_id):
        with self.lock:
            if self.job:
                raise BusyError("BUSY")
            if self.state != "READY":
                raise ValueError("카메라가 준비되지 않았습니다.")
            if not self.candidate or self.candidate["request_id"] != candidate_id:
                raise ValueError("현재 기준 이미지와 일치하지 않습니다.")
            confirmed = dict(self.candidate, confirmed=True, confirmed_at=utc_now(),
                             confirmation_basis="human_review_of_live_reference_overlay")
            atomic_write(self.output / candidate_id / "calibration_confirmed.json",
                         json.dumps(confirmed, ensure_ascii=False, indent=2).encode())
            self.calibration = confirmed
            return confirmed

    def _preview(self, camera):
        import cv2
        frame = camera.capture()
        ok, jpeg = cv2.imencode(".jpg", frame.image, [cv2.IMWRITE_JPEG_QUALITY, 75])
        if not ok:
            raise RuntimeError("PREVIEW_ENCODING_FAILED")
        with self.lock:
            self.preview = jpeg.tobytes()
            self.last_frame_time = time.monotonic()
        return frame, dict(camera.frame_info)

    def _quality(self, image):
        import cv2
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        brightness = float(gray.mean())
        sharpness = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        valid = (self.config["min_mean_brightness"] <= brightness <= self.config["max_mean_brightness"]
                 and sharpness >= self.config["min_blur_variance"])
        return {"valid": valid, "mean_brightness": brightness, "laplacian_variance": sharpness,
                "scope": "global image quality only; not slot occlusion verification"}

    def _execute(self, job, camera, detector):
        import cv2
        observations, frames = [], []
        after = job["accepted_monotonic"] + self.config["frame_spacing_seconds"]
        while len(frames) < self.config["frames_per_inspection"]:
            if self.stopping.is_set() or time.monotonic() > job["deadline"]:
                raise TimeoutError("INSPECTION_TIMEOUT_OR_STOP")
            frame, freshness = self._preview(camera)
            if (freshness["estimated_source_monotonic"] < after
                    or freshness["age_seconds"] > self.config["frame_max_age_seconds"]):
                continue
            value = detector.detect(frame).to_dict()
            value.update(freshness=freshness, captured_at=frame.captured_at.isoformat(), quality=self._quality(frame.image))
            observations.append(value)
            frames.append(frame)
            after = freshness["estimated_source_monotonic"] + self.config["frame_spacing_seconds"]
        if time.monotonic() > job["deadline"]:
            raise TimeoutError("INSPECTION_TIMEOUT")
        candidate = None
        if job["kind"] == "calibrate":
            proposals = [calibrate(item["detections"], self.config) for item in observations]
            if not all(item["quality"]["valid"] for item in observations):
                raise ValueError("기준 영상 품질이 부족합니다.")
            candidate = dict(proposals[-1], request_id=job["request_id"], config_sha256=self.config_hash)
            decision = {"status": "REVIEW", "reason": "보라색 검사 자리와 실제 부품 위치를 확인해주세요."}
        else:
            decision = decide(observations, self.calibration, self.config, job["visibility_confirmed"])
        result = dict(job, **decision, observations=observations, backend=self.backend,
                      model_sha256=detector.model_hash, config_sha256=self.config_hash,
                      product_id=self.config["product_id"], config_version=self.config["version"],
                      calibration=self.calibration, candidate=candidate, source="live", mode="BENCH_EDGE",
                      input_shape=detector.input_shape, completed_at=utc_now(),
                      inference_ms=sum(item["inference_ms"] for item in observations),
                      limitations=self.config["limitations"])
        directory = self.output / job["request_id"]
        assets = []
        for frame in frames:
            ok, encoded = cv2.imencode(".png", frame.image)
            if not ok:
                raise OSError("PNG_ENCODE_FAILED")
            data = encoded.tobytes()
            name = frame.frame_id + ".png"
            atomic_write(directory / name, data)
            assets.append({"filename": name, "sha256": digest(data), "frame_id": frame.frame_id,
                           "width": frame.width, "height": frame.height, "kind": "raw"})
        overlay = frames[-1].image.copy()
        for detection in observations[-1]["detections"]:
            box = detection["bounding_box"]
            x1, y1, x2, y2 = [round(box[k]) for k in ("x1", "y1", "x2", "y2")]
            cv2.rectangle(overlay, (x1, y1), (x2, y2), (0, 220, 0), 2)
            cv2.putText(overlay, f'{detection["class_name"]} {detection["confidence"]:.3f}',
                        (x1, max(20, y1 - 5)), cv2.FONT_HERSHEY_SIMPLEX, .6, (0, 220, 0), 2)
        regions = candidate or self.calibration
        if regions:
            for slot_id, box in regions["slots"].items():
                x1, y1, x2, y2 = map(round, box)
                cv2.rectangle(overlay, (x1, y1), (x2, y2), (230, 50, 230), 2)
                cv2.putText(overlay, "EXPECTED SLOT " + slot_id, (x1, y2 + 20), cv2.FONT_HERSHEY_SIMPLEX, .5, (230, 50, 230), 1)
        ok, encoded = cv2.imencode(".jpg", overlay)
        if not ok:
            raise OSError("OVERLAY_ENCODE_FAILED")
        atomic_write(directory / "overlay.jpg", encoded.tobytes())
        result.update(assets=assets, storage_success=True,
                      inspection_total_ms=(time.monotonic() - job["accepted_monotonic"]) * 1000)
        atomic_write(directory / "result.json", json.dumps(result, ensure_ascii=False, indent=2).encode())
        with self.lock:
            self.last_result, self.last_overlay = result, encoded.tobytes()
            if candidate:
                self.candidate = candidate
                self.calibration = None

    def run(self):
        camera = None
        try:
            from src.camera.gstreamer_camera import GStreamerCamera
            from src.vision.pytorch_detector import PyTorchDetector
            detector = (self.detector_factory or PyTorchDetector)(
                self.model_path, self.config["model_sha256"], self.config["classes"],
                self.config["detection_confidence"], self.config["nms_iou"])
            camera = (self.camera_factory or GStreamerCamera)(self.config["camera"])
            with self.lock:
                self.backend.update(device=detector.device, gpu=detector.torch.cuda.get_device_name(0),
                                    camera_pipeline=camera.pipeline_text)
            while not self.stopping.is_set():
                self._preview(camera)
                with self.lock:
                    job = self.job
                    if job is None:
                        self.state = "READY"
                if job:
                    try:
                        self._execute(job, camera, detector)
                    except Exception as error:
                        failure = dict(job, status="ERROR", reason=str(error), backend=self.backend,
                                       model_sha256=self.config["model_sha256"], config_sha256=self.config_hash,
                                       visibility_confirmed=job["visibility_confirmed"], source="live",
                                       completed_at=utc_now(), storage_success=False)
                        try:
                            atomic_write(self.output / job["request_id"] / "error.json",
                                         json.dumps(failure, ensure_ascii=False, indent=2).encode())
                        except OSError:
                            failure["failure_record_saved"] = False
                        with self.lock:
                            self.last_result, self.last_overlay = failure, None
                            self.error = str(error)
                        if isinstance(error, OSError):
                            raise
                    finally:
                        with self.lock:
                            self.job = None
                            self.state = "READY"
        except Exception as error:
            with self.lock:
                active = self.job
            if active:
                failure = dict(active, status="ERROR", reason=str(error), backend=self.backend,
                               completed_at=utc_now(), storage_success=False, source="live")
                try:
                    atomic_write(self.output / active["request_id"] / "error.json",
                                 json.dumps(failure, ensure_ascii=False, indent=2).encode())
                except OSError:
                    failure["failure_record_saved"] = False
                with self.lock:
                    self.last_result, self.last_overlay, self.job = failure, None, None
            with self.lock:
                self.state, self.error, self.preview = "ERROR", f"{type(error).__name__}: {error}", None
        finally:
            if camera:
                camera.close()


def make_handler(worker, token):
    class Handler(BaseHTTPRequestHandler):
        def respond(self, code, data, content_type="application/json; charset=utf-8"):
            if not isinstance(data, bytes):
                data = json.dumps(data, ensure_ascii=False).encode()
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            try:
                self.wfile.write(data)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def do_GET(self):
            path = urlsplit(self.path).path
            if path == "/":
                html = Path(__file__).with_name("bench.html").read_text(encoding="utf-8")
                self.respond(200, html.replace("__TOKEN__", token).encode(), "text/html; charset=utf-8")
            elif path == "/api/status":
                self.respond(200, worker.snapshot())
            elif path in ("/preview.jpg", "/result.jpg"):
                with worker.lock:
                    data = worker.preview if path == "/preview.jpg" else worker.last_overlay
                if path == "/preview.jpg" and not worker.snapshot()["camera_current"]:
                    data = None
                self.respond(200 if data else 503, data or b"Image unavailable", "image/jpeg" if data else "text/plain")
            else:
                self.respond(404, {"error": "NOT_FOUND"})

        def do_POST(self):
            if self.headers.get("X-Bench-Token") != token:
                self.respond(403, {"error": "INVALID_TOKEN"})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length < 1 or length > 2048:
                    raise ValueError("INVALID_BODY_SIZE")
                body = json.loads(self.rfile.read(length))
                if self.path in ("/api/inspect", "/api/calibrate"):
                    request_id = worker.submit(self.path.rsplit("/", 1)[-1], body.get("visibility_confirmed"))
                    self.respond(202, {"request_id": request_id})
                elif self.path == "/api/confirm-calibration":
                    self.respond(200, worker.confirm_calibration(body.get("request_id")))
                else:
                    self.respond(404, {"error": "NOT_FOUND"})
            except BusyError as error:
                self.respond(409, {"error": str(error)})
            except (ValueError, TypeError, AttributeError) as error:
                self.respond(400, {"error": str(error)})
            except OSError:
                self.respond(503, {"error": "PERSISTENCE_ERROR"})

        def log_message(self, format, *args):
            if args and str(args[0]).startswith("POST"):
                super().log_message(format, *args)
    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--port", type=int, default=8767)
    args = parser.parse_args()
    if platform.machine() != "aarch64" or not Path("/etc/nv_tegra_release").exists():
        raise RuntimeError("Live BENCH requires Jetson; no Windows inference fallback")
    config_bytes = args.config.read_bytes()
    worker = BenchWorker(json.loads(config_bytes), config_bytes, args.model, args.output)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(worker, uuid.uuid4().hex))
    server.daemon_threads = True
    def stop(signum, frame):
        worker.stopping.set()
        threading.Thread(target=server.shutdown, daemon=True).start()
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    worker.start()
    print(f"BENCH listening on 127.0.0.1:{args.port}; worker initialization pending", flush=True)
    try:
        server.serve_forever()
    finally:
        worker.stopping.set()
        worker.join(timeout=3)
        server.server_close()


if __name__ == "__main__":
    main()
