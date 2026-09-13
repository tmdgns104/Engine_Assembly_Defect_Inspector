"""Run four staged raw frames on target GPU; evaluation truth stays outside Detector."""

import argparse
import hashlib
import json
import platform
import time
from datetime import datetime, timezone
from pathlib import Path

import cv2

from src.contracts import CameraFrame
from src.vision.pytorch_detector import PyTorchDetector


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--staging", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if platform.machine() != "aarch64" or not Path("/etc/nv_tegra_release").exists():
        raise RuntimeError("This evidence runner requires an actual Jetson")
    manifest = json.loads((args.staging / "manifest.json").read_text())
    names = [manifest["classes"][str(i)] for i in range(len(manifest["classes"]))]
    args.output.mkdir(parents=True, exist_ok=False)
    initialized = time.perf_counter()
    detector = PyTorchDetector(args.model, manifest["model_sha256"], names)
    startup_ms = (time.perf_counter() - initialized) * 1000
    results = []
    for item in manifest["images"]:
        path = args.staging / item["image"]
        if hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"]:
            raise ValueError("IMAGE_HASH_MISMATCH")
        image = cv2.imread(str(path))
        if image is None:
            raise ValueError("IMAGE_DECODE_FAILED")
        height, width = image.shape[:2]
        frame = CameraFrame(image, item["capture_id"], datetime.now(timezone.utc), width, height, "replay")
        detection = detector.detect(frame)
        value = detection.to_dict()
        value.update(image=item["image"], image_sha256=item["sha256"],
                     actual_input_shape=detector.input_shape, source="replay", device=detector.device)
        results.append(value)
        overlay = image.copy()
        for obj in detection.detections:
            box = obj.bounding_box
            cv2.rectangle(overlay, (round(box.x1), round(box.y1)), (round(box.x2), round(box.y2)), (0, 200, 0), 2)
            cv2.putText(overlay, f"{obj.class_name} {obj.confidence:.3f}", (round(box.x1), max(20, round(box.y1)-5)), cv2.FONT_HERSHEY_SIMPLEX, .6, (0, 200, 0), 2)
        if not cv2.imwrite(str(args.output / (item["capture_id"] + ".png")), overlay):
            raise OSError("SMOKE_OVERLAY_WRITE_FAILED")
    expectations = json.loads((args.staging / "smoke_expectations.json").read_text())
    checks = []
    for observed, truth in zip(results, expectations):
        removed = set(truth["provenance"]["objects_removed"])
        expected = sorted(set(names) - removed)
        actual = sorted(obj["class_name"] for obj in observed["detections"])
        checks.append({"scenario": truth["scenario"], "expected": expected, "actual": actual,
                       "pass": actual == expected, "capture_id": observed["frame_id"]})
    report = {"hostname": platform.node(), "machine": platform.machine(), "backend": "pytorch",
              "device": detector.device, "gpu": detector.torch.cuda.get_device_name(0),
              "model_sha256": detector.model_hash, "startup_ms": startup_ms,
              "input": "full BGR frame -> Ultralytics RGB/255 float32 letterbox 640x640, rect=False",
              "conf": .25, "nms_iou": .7, "augment": False, "roi_crop": False,
              "onnx_parity": "NOT_RUN_PT_PATH", "results": results, "checks": checks,
              "scope": "four-image deployment smoke; not full accuracy or live decision validation"}
    (args.output / "result.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(json.dumps({"backend": report["backend"], "device": report["device"], "checks": checks}, indent=2))
    if not all(item["pass"] for item in checks):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
