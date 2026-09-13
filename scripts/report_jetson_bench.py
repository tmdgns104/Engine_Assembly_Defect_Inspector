"""Summarize observed deployment evidence without upgrading pending live tests to PASS."""

import hashlib
import json
import math
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "runs/jetson_bench_001"


def load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main():
    smoke = load(RUN / "smoke_v001/result.json")
    environment = load(RUN / "jetson_environment_v001.json")
    frames = load(RUN / "camera_timestamp_check.json")
    assert smoke["device"] == "cuda:0" and smoke["machine"] == "aarch64"
    assert len(smoke["checks"]) == 4 and all(item["pass"] for item in smoke["checks"])
    for result in smoke["results"]:
        assert result["actual_input_shape"] == [1, 3, 640, 640]
        for obj in result["detections"]:
            box = obj["bounding_box"]
            assert 0 <= box["x1"] < box["x2"] <= 1280
            assert 0 <= box["y1"] < box["y2"] <= 720
            assert math.isfinite(obj["confidence"]) and 0 <= obj["confidence"] <= 1
    assert all(b["source_pts_ns"] > a["source_pts_ns"] for a, b in zip(frames, frames[1:]))
    hashes = {}
    for line in (RUN / "deployed_checksums_and_tests.txt").read_text(encoding="utf-8-sig").splitlines():
        parts = line.split(maxsplit=1)
        if len(parts) == 2 and len(parts[0]) == 64:
            target = parts[1].strip()
            local = ROOT / target
            if target == "best.pt":
                local = ROOT / "training/experiments/earbud_case_v0_20260913_v001/baseline/weights/best.pt"
            digest = hashlib.sha256(local.read_bytes()).hexdigest()
            assert digest == parts[0], target
            hashes[target] = digest
    assert len(hashes) == 8
    with urllib.request.urlopen("http://127.0.0.1:8767/api/status", timeout=5) as response:
        status = json.load(response)
    assert status["state"] == "READY" and status["camera_current"]
    with urllib.request.urlopen("http://127.0.0.1:8767/", timeout=5) as response:
        html = response.read().decode()
    assert "검사하기" in html and "__TOKEN__" not in html
    report = {
        "task": "JETSON-BENCH-001", "status": "IN_PROGRESS_AWAITING_HUMAN_LIVE_TEST",
        "environment": {"hostname": environment["hostname"], "machine": environment["machine"],
                        "python": environment["python"], "l4t": "36.4.7", "torch": environment["torch"]["version"],
                        "cuda_build": environment["torch"]["cuda_build"], "ultralytics": environment["ultralytics"]["version"],
                        "opencv": environment["cv2"]["version"], "tensorrt_installed_unused": environment["tensorrt"]["version"]},
        "backend": "PyTorch CUDA", "device": smoke["device"], "deployment_hashes_match": hashes,
        "onnx_parity": "NOT_RUN_PT_PATH", "b03_smoke": smoke["checks"],
        "model_startup_ms": smoke["startup_ms"],
        "smoke_predict_ms_including_first_call_initialization": [x["inference_ms"] for x in smoke["results"]],
        "timing_scope": "4 smoke images; not a latency benchmark. First prediction is cold; remaining 3 are warm.",
        "camera": {"timestamp_frames": len(frames), "increasing_pts": True,
                   "min_age_seconds": min(x["age_seconds"] for x in frames),
                   "max_age_seconds": max(x["age_seconds"] for x in frames),
                   "sensor_exposure_timestamp_verified": False,
                   "pipeline": status["backend"]["camera_pipeline"]},
        "automatic_tests": {"windows_contracts": 19, "jetson_contracts": 19,
                            "windows_bench": 11, "jetson_bench": 11, "result": "PASS"},
        "http_status_and_preview": "PASS", "browser_human_review": "PENDING",
        "live_four_states": "NOT_RUN", "physical_camera_disconnect": "NOT_RUN",
        "duplicate_http_live_request": "NOT_RUN", "file_db_scope": "PNG/JSON implementation; DB not implemented",
        "target_root": "/home/jetson/oned_device_bench/releases/bench_v001",
        "browser_url": "http://127.0.0.1:8767", "bind": "Jetson 127.0.0.1 via SSH tunnel",
        "excluded": ["B04", "retraining", "ROI tuning", "MES", "PLC", "engine hardware verification"]}
    path = ROOT / "docs/verification/JETSON-BENCH-001-20260913.json"
    with path.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
    print(json.dumps({"status": report["status"], "hashes_checked": len(hashes), "path": str(path)}, indent=2))


if __name__ == "__main__":
    main()
