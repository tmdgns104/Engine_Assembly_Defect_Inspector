"""Persistent camera/model owner process. No final file writes, SQLite, or PLC commands."""

import queue
import threading
import time
import socket
from datetime import datetime, timezone

from src.decision.slots import assess, pixel_box
from src.decision.calibration import ReferenceError, reference_proposal, station_fingerprint
from src.quality.image import assess_image
from src.recipe.package import load_package


def put_latest(channel, value):
    try:
        channel.put_nowait(value)
    except queue.Full:
        try:
            channel.get_nowait()
        except queue.Empty:
            pass
        try:
            channel.put_nowait(value)
        except queue.Full:
            pass


def encode_evidence(frame, observations, recipe, calibration):
    import cv2
    images = []
    for original in frame:
        ok, encoded = cv2.imencode(".png", original.image)
        if not ok:
            raise OSError("PNG_ENCODE_FAILED")
        images.append({"data": encoded.tobytes(), "kind": "raw", "width": original.width,
                       "height": original.height, "capture_at": original.captured_at.isoformat(), "view": "top"})
    last = frame[-1]
    overlay = last.image.copy()
    for item in observations[-1]["detections"]:
        box = item["bounding_box"]
        x1,y1,x2,y2 = [round(box[k]) for k in ("x1","y1","x2","y2")]
        cv2.rectangle(overlay,(x1,y1),(x2,y2),(0,220,0),2)
        cv2.putText(overlay,f'{item["class_name"]} {item["confidence"]:.3f}',(x1,max(20,y1-5)),cv2.FONT_HERSHEY_SIMPLEX,.6,(0,220,0),2)
    # No candidate means no authoritative expected slots to draw.
    regions = calibration["slots"] if calibration else {}
    for slot in recipe["slots"]:
        if slot['id'] not in regions:
            continue
        x1,y1,x2,y2 = map(round,pixel_box(regions[slot["id"]],last.width,last.height))
        cv2.rectangle(overlay,(x1,y1),(x2,y2),(230,50,230),2)
        cv2.putText(overlay,"EXPECTED "+slot["id"],(x1,min(last.height-5,y2+20)),cv2.FONT_HERSHEY_SIMPLEX,.5,(230,50,230),1)
    ok, encoded = cv2.imencode(".jpg", overlay)
    if not ok:
        raise OSError("OVERLAY_ENCODE_FAILED")
    images.append({"data": encoded.tobytes(), "kind": "overlay", "width": last.width,
                   "height": last.height, "capture_at": last.captured_at.isoformat(), "view": "top"})
    return images


def worker_main(package_root, station, generation, commands, results, previews, stopping, cancellation, heartbeat):
    from src.camera.gstreamer_camera import GStreamerCamera
    from src.vision.pytorch_detector import PyTorchDetector
    import cv2
    camera = None
    def pulse():
        while not stopping.wait(.5):
            heartbeat.value = time.monotonic()
    threading.Thread(target=pulse, daemon=True).start()
    try:
        package = load_package(package_root)
        start = time.monotonic()
        detector = PyTorchDetector(package.model_path, package.manifest["files"]["model"]["sha256"], package.names,
                                   package.preprocessing["confidence"],package.preprocessing["nms_iou"],package.preprocessing)
        if "self_test" in package.manifest["files"]:
            from src.contracts import CameraFrame
            image = cv2.imread(str(package.root / package.manifest["files"]["self_test"]["path"]))
            if image is None:
                raise RuntimeError("PACKAGE_SELF_TEST_IMAGE_INVALID")
            frame = CameraFrame(image,"package-self-test",datetime.now(timezone.utc),image.shape[1],image.shape[0],"replay")
            detector.detect(frame)
        camera = GStreamerCamera(dict(package.capture, device=station["camera_device"]))
        first = camera.capture()
        backend = {"backend": "pytorch", "device": detector.device, "gpu": detector.torch.cuda.get_device_name(0),
                   'hostname':socket.gethostname(),
                   "input_shape": detector.input_shape, "camera_pipeline": camera.pipeline_text,
                   "load_self_test_ms": (time.monotonic()-start)*1000}
        results.put({"type": "ready", "generation": generation, "backend": backend}, timeout=2)
        while not stopping.is_set():
            frame = camera.capture()
            ok, jpeg = cv2.imencode(".jpg",frame.image,[cv2.IMWRITE_JPEG_QUALITY,75])
            if not ok:
                raise RuntimeError("PREVIEW_ENCODING_FAILED")
            put_latest(previews,{"jpeg": jpeg.tobytes(), "generation": generation, "freshness": dict(camera.frame_info)})
            try:
                job = commands.get_nowait()
            except queue.Empty:
                continue
            observations, frames = [], []
            after = job["accepted_monotonic"] + station["frame_spacing_seconds"]
            try:
                while len(frames) < package.recipe["observation_count"]:
                    if stopping.is_set() or cancellation.is_set() or time.monotonic() > job["deadline"]:
                        raise TimeoutError("CANCELLED_OR_EXPIRED")
                    frame = camera.capture()
                    freshness = dict(camera.frame_info)
                    if freshness["estimated_source_monotonic"] < after or freshness["age_seconds"] > station["max_frame_age_seconds"]:
                        continue
                    detected = detector.detect(frame).to_dict()
                    detected.update(width=frame.width,height=frame.height,freshness=freshness,
                                    quality=assess_image(frame.image,station["quality"]),captured_at=frame.captured_at.isoformat())
                    frames.append(frame); observations.append(detected)
                    after = freshness["estimated_source_monotonic"] + station["frame_spacing_seconds"]
                candidate = None
                if job["request"]["kind"] == "calibrate":
                    try:
                        candidate = reference_proposal(observations,package)
                        candidate.update(source_inspection_id=job['inspection_id'], station_id=station['station_id'],
                                         cell_id=station['cell_id'], station_sha256=station_fingerprint(station))
                        result = {"decision": "REVIEW", "reason": "검사 자리와 제품 구도를 화면에서 확인하세요.", "defects": [], "unassessed": []}
                    except ReferenceError as error:
                        result = {"decision": "REVIEW", "reason": str(error), "reason_code": error.code,
                                  "defects": [], "unassessed": error.slots}
                else:
                    result = assess(observations,package.recipe,job["request"]["view_assessment"],job.get("calibration"))
                displayed_calibration = candidate if job['request']['kind'] == 'calibrate' else job.get('calibration')
                result.update(observations=observations,calibration_candidate=candidate,
                              calibration_used=displayed_calibration,backend=backend,
                              inference_ms=sum(item["inference_ms"] for item in observations),
                              worker_total_ms=(time.monotonic()-job["accepted_monotonic"])*1000,
                              visibility_limit="Human-assisted visibility; automatic occlusion/orientation recognition unverified")
                images = encode_evidence(frames,observations,package.recipe,displayed_calibration)
                results.put({"type":"result","generation":generation,"inspection_id":job["inspection_id"],"result":result,"images":images},timeout=2)
            except Exception as error:
                results.put({"type":"result","generation":generation,"inspection_id":job["inspection_id"],
                             "result":{"decision":"ERROR","reason":f"{type(error).__name__}: {error}","defects":[],"unassessed":[]},"images":[]},timeout=2)
    except Exception as error:
        try:
            results.put({"type":"fault","generation":generation,"error":f"{type(error).__name__}: {error}"},timeout=2)
        except queue.Full:
            pass
    finally:
        stopping.set()
        if camera:
            camera.close()
