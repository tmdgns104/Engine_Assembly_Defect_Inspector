"""Verify the existing baseline and stage four raw B03 smoke images, never B04."""

import argparse
import ast
import hashlib
import json
import shutil
from pathlib import Path


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def prepare(root, output):
    import onnx
    import onnxruntime
    from ultralytics import YOLO

    experiment = root / "training/experiments/earbud_case_v0_20260913_v001"
    result = read_json(experiment / "baseline_result.json")
    weights = experiment / "baseline/weights"
    model = weights / "best.pt"
    onnx_path = weights / "best.onnx"
    recorded = result["checkpoints"]["best.pt"]
    if Path(recorded["path"]).resolve() != model.resolve() or sha256(model) != recorded["sha256"]:
        raise ValueError("Baseline checkpoint provenance mismatch")
    expected_classes = ["earbud_left", "earbud_right", "case"]
    classes = YOLO(str(model)).names
    if [classes[index] for index in range(len(classes))] != expected_classes:
        raise ValueError("Unexpected PT classes")
    graph = onnx.load(str(onnx_path))
    onnx.checker.check_model(graph)
    metadata = {item.key: item.value for item in graph.metadata_props}
    if ast.literal_eval(metadata["names"]) != classes:
        raise ValueError("ONNX/PT class mapping mismatch")
    session = onnxruntime.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
    io = lambda item: {"name": item.name, "shape": item.shape, "type": item.type}
    onnx_info = {"sha256": sha256(onnx_path), "inputs": [io(x) for x in session.get_inputs()],
                 "outputs": [io(x) for x in session.get_outputs()], "metadata": metadata,
                 "opset": [item.version for item in graph.opset_import],
                 "nms_nodes": sum(node.op_type == "NonMaxSuppression" for node in graph.graph.node),
                 "parity": "NOT_RUN", "session_provider": session.get_providers(),
                 "inference_executed": False}
    split_path = root / "training/outputs/datasets/earbud_case_v0_B01_B03_20260913_v001/split_manifest.json"
    # Only the public development validation records are selected. Never traverse test/raw folders.
    validation = read_json(split_path)["val"]
    scenarios = ["NORMAL", "MISSING_LEFT", "MISSING_RIGHT", "MISSING_BOTH"]
    selected = []
    for scenario in scenarios:
        matches = [row for row in validation
                   if row["provenance"]["round_id"] == "B03"
                   and row["provenance"]["scenario"] == scenario
                   and row["provenance"]["condition_id"] == "BASE"
                   and row["provenance"]["placement_id"] == "CENTER"]
        if len(matches) != 1:
            raise ValueError(f"Expected one B03 BASE CENTER representative: {scenario}")
        row = matches[0]
        raw = Path(row["provenance"]["image_path"])
        if sha256(raw) != row["image_sha256"]:
            raise ValueError(f"Raw source hash mismatch: {row['filename']}")
        selected.append((row, raw))
    # Refuse overwrite, including a failed previous preparation. Recovery is explicit.
    output.mkdir(parents=True, exist_ok=False)
    (output / "images").mkdir()
    items = []
    evaluation = []
    for row, raw in selected:
        destination = output / "images" / (row["provenance"]["capture_id"] + ".png")
        shutil.copyfile(raw, destination)
        if sha256(destination) != row["image_sha256"]:
            raise ValueError("Staged image hash mismatch")
        relative = destination.relative_to(output).as_posix()
        items.append({"image": relative, "sha256": row["image_sha256"],
                      "capture_id": row["provenance"]["capture_id"]})
        evaluation.append({"image": relative, "filename": row["filename"],
                           "scenario": row["provenance"]["scenario"],
                           "provenance": row["provenance"]})
    report = {"status": "PREPARED_NOT_DEPLOYED", "model_path": str(model),
              "model_sha256": sha256(model), "classes": classes, "onnx": onnx_info,
              "split_manifest_sha256": sha256(split_path), "images": items,
              "gpu_backend": "PENDING_JETSON_PROBE", "jetson_execution": "NOT_RUN",
              "preprocessing": {"full_frame": True, "roi_crop": False,
                                "clahe": False, "sharpening": False, "augment": False}}
    (output / "manifest.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (output / "smoke_expectations.json").write_text(json.dumps(evaluation, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": report["status"], "model_sha256": report["model_sha256"],
                      "classes": classes, "onnx_inputs": onnx_info["inputs"],
                      "onnx_outputs": onnx_info["outputs"], "nms_nodes": onnx_info["nms_nodes"],
                      "sample_count": len(items), "output": str(output)}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    options = parser.parse_args()
    prepare(Path(__file__).resolve().parents[1], options.output.resolve())
