"""Synthetic package and worker fixtures shared by notebook runtime checks."""
import queue
import time

from src.recipe.package import canonical, sha256


def fixture_documents():
    recipe = {"schema_version": 1, "recipe_id": "assembly", "version": "1", "coordinate_space": "normalized_image",
              "alignment_mode": "fixed_profile", "visibility_mode": "human_per_request", "rule": "presence_count",
              "reference_class": None, "presence_confidence": .8, "reference_confidence": .8,
              "slot_overlap": .65, "reference_iou": .65, "observation_count": 3,
              "required_views": ["top"], "orientation_verified": False,
              "slots": [{"id": "first", "allowed_classes": ["bolt"], "display": "첫 자리", "expected_count": 2, "region": [0, 0, .45, 1]},
                        {"id": "second", "allowed_classes": ["bolt"], "display": "다음 자리", "expected_count": 1, "region": [.55, 0, 1, 1]}]}
    preprocessing = {"input_layout": "NCHW", "source_color": "BGR", "model_color": "RGB", "normalization": "divide_255",
                     "dtype": "float32", "resize": "letterbox", "interpolation": "linear", "padding": 114,
                     "rect": False, "crop": False, "nms_location": "ultralytics", "augmentation": False,
                     "size": [768, 960], "confidence": .25, "nms_iou": .7}
    return {"classes": {"classes": [{"id": index, "name": name} for index, name in enumerate(["base", "bolt", "cover", "washer"])]},
            "preprocessing": preprocessing, "recipe": recipe,
            "capture": {"width": 1280, "height": 720, "fps": 30, "format": "MJPG", "view": "top"}}


def write_package(root, documents=None):
    root.mkdir(parents=True, exist_ok=True)
    manifest = {"schema_version": 1, "enabled": True, "release_id": "fixture-v1", "product_id": "fixture", "model_version": "mock",
                "detector": {"backend": "pytorch", "task": "detect", "output": "ultralytics_xyxy"}, "files": {}}
    for key, value in {"model": b"fixture-not-a-real-model", **(documents or fixture_documents())}.items():
        data = value if isinstance(value, bytes) else canonical(value).encode()
        filename = "best.pt" if key == "model" else key + ".json"
        (root / filename).write_bytes(data)
        manifest["files"][key] = {"path": filename, "sha256": sha256(data)}
    (root / "manifest.json").write_text(canonical(manifest), encoding="utf-8")
    return manifest


def trigger_worker(package_root, station, generation, commands, results, previews, stopping, cancellation, heartbeat):
    results.put({'type': 'ready', 'generation': generation, 'backend': {'backend': 'mock'}})
    while not stopping.wait(.01):
        heartbeat.value = time.monotonic()
        try:
            previews.put_nowait({'generation': generation, 'jpeg': b'synthetic', 'freshness': {'camera_epoch': 'test-camera'}})
        except queue.Full:
            pass
        try:
            job = commands.get_nowait()
        except queue.Empty:
            continue
        time.sleep(.15)
        results.put({'type': 'result', 'generation': generation, 'inspection_id': job['inspection_id'],
                     'result': {'decision': 'REVIEW', 'reason': 'SYNTHETIC', 'fresh_frame': {'trigger': job['trigger']}},
                     'images': [{'kind': 'raw', 'data': b'synthetic', 'width': 1, 'height': 1}]})
