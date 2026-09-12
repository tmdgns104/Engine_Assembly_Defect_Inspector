"""Read-only verification of one completed capture session; no camera access."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import sys

if __package__:
    from . import capture_proxy as capture
else:
    import capture_proxy as capture


def verify_session(output_root: Path, session_id: str) -> dict:
    import cv2

    capture.validate_ids(session_id, session_id + "_CHECK")
    root = Path(os.path.abspath(output_root))
    session = root / session_id
    capture.plain_path(session)
    if (session / ".capture.lock").exists():
        raise capture.CaptureError("Session is active or interrupted; verify after writer exits")
    records = capture.read_manifest(session / "manifest.jsonl")
    if not records:
        raise capture.CaptureError("No recorded captures in session")
    images = []
    for record in records:
        if record["session_id"] != session_id:
            raise capture.CaptureError("Manifest session_id mismatch")
        path = root / record["image_path"]
        capture.plain_path(path)
        data = path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        if len(data) != record["image_bytes"] or digest != record["image_sha256"]:
            raise capture.CaptureError(f"Image size/hash mismatch: {path}")
        image = cv2.imread(str(path), cv2.IMREAD_COLOR)
        if image is None or image.shape[:2] != (record["height"], record["width"]):
            raise capture.CaptureError(f"Image reload/dimensions failed: {path}")
        images.append({"capture_id": record["capture_id"], "image_path": record["image_path"],
                       "width": record["width"], "height": record["height"],
                       "bytes": len(data), "sha256": digest})
    if set(session.glob("*/images/*.png")) != {root / row["image_path"] for row in records}:
        raise capture.CaptureError("Orphan PNG files or manifest/image set mismatch")
    profile = records[0].get("profile_snapshot")
    return {"status": "verified", "session_id": session_id, "captures": len(images), "images": images,
            "schema_version": records[0]["schema_version"],
            "product_id": profile["product_id"] if profile is not None else None,
            "profile_version": profile["profile_version"] if profile is not None else None,
            "profile_sha256": records[0].get("profile_sha256"),
            "source_counts": dict(Counter(row["source_kind"] for row in records)),
            "scenario_counts": dict(Counter(row["scenario"] for row in records)),
            "record_semantics": "capture_intent_not_inspection_result"}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--session-id", required=True)
    args = parser.parse_args(argv)
    try:
        import cv2
    except ImportError as exc:
        print(f"VERIFY_ERROR: OpenCV required: {exc}", file=sys.stderr)
        return 1
    try:
        print(json.dumps(verify_session(args.output_root, args.session_id), ensure_ascii=False))
        return 0
    except (capture.CaptureError, ValueError, OSError, cv2.error) as exc:
        print(f"VERIFY_ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
