"""One-shot, headless dataset acquisition; not a production Camera adapter.

The storage/metadata functions use only the standard library. OpenCV is imported
only for actual camera or sample-image decoding. Compatible with Python 3.10+.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import sys
import uuid


OBJECTS = ["OBJ_A", "OBJ_B", "OBJ_C"]
SCENARIOS = (
    "NORMAL", "MISSING_A", "MISSING_B", "MISSING_C", "EXTRA_OBJECT",
    "POSITION_SHIFT", "OCCLUSION", "BLUR", "LOW_EXPOSURE", "CAMERA_SMOKE",
)
ID_PATTERN = r"[A-Z][A-Z0-9_-]{0,31}"
EPISODE_PATTERN = r"[A-Z][A-Z0-9_-]{0,79}"
RESERVED = {"CON", "PRN", "AUX", "NUL", *[f"COM{i}" for i in range(1, 10)],
            *[f"LPT{i}" for i in range(1, 10)]}
FIELDS = {
    "schema_version", "capture_id", "session_id", "episode_id", "scenario",
    "captured_at", "object_configuration", "device", "camera_source", "source_kind",
    "width", "height", "image_path", "image_bytes", "image_sha256", "notes",
}
EPISODE_FIELDS = ("scenario", "object_configuration", "source_kind", "device", "camera_source", "width", "height")


class CaptureError(RuntimeError):
    """Actionable acquisition/storage failure; CLI returns a nonzero exit code."""


def validate_ids(session_id: str, episode_id: str) -> None:
    if not isinstance(session_id, str) or not re.fullmatch(ID_PATTERN, session_id):
        raise ValueError("session_id: use 1-32 uppercase ASCII letters/digits/_/-; start with a letter")
    if session_id in RESERVED:
        raise ValueError("session_id is a reserved Windows filename")
    if not isinstance(episode_id, str) or not re.fullmatch(EPISODE_PATTERN, episode_id):
        raise ValueError("episode_id: use 1-80 uppercase ASCII letters/digits/_/-")
    if not episode_id.startswith(session_id + "_"):
        raise ValueError("episode_id must start with session_id plus underscore")


def object_configuration(scenario: str) -> dict:
    if scenario not in SCENARIOS:
        raise ValueError(f"unknown scenario: {scenario}")
    removed = ["OBJ_" + scenario[-1]] if scenario.startswith("MISSING_") else []
    return {
        "objects_expected": [] if scenario == "CAMERA_SMOKE" else list(OBJECTS),
        "objects_removed": removed,
        "unexpected_object": scenario == "EXTRA_OBJECT",
    }


def utc_time(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("captured_at must be a timezone-aware datetime")
    return value.astimezone(timezone.utc)


def make_record(*, session_id: str, episode_id: str, scenario: str,
                captured_at: datetime, width: int, height: int, device: str,
                camera_source: str, source_kind: str, image_png: bytes,
                notes: str = "") -> dict:
    """Create intent metadata, never an annotation or a verified object-presence claim."""
    validate_ids(session_id, episode_id)
    captured_at = utc_time(captured_at)
    capture_id = episode_id + "_" + captured_at.strftime("%Y%m%dT%H%M%S%fZ") + "_" + uuid.uuid4().hex[:12]
    record = {
        "schema_version": 1, "capture_id": capture_id, "session_id": session_id,
        "episode_id": episode_id, "scenario": scenario,
        "captured_at": captured_at.isoformat(), "object_configuration": object_configuration(scenario),
        "device": device, "camera_source": camera_source, "source_kind": source_kind,
        "width": width, "height": height,
        "image_path": f"{session_id}/{episode_id}/images/{capture_id}.png",
        "image_bytes": len(image_png), "image_sha256": hashlib.sha256(image_png).hexdigest(),
        "notes": notes,
    }
    validate_record(record)
    return record


def validate_record(record: dict) -> None:
    """Normative executable schema; unknown keys (including labels) are rejected."""
    if not isinstance(record, dict) or set(record) != FIELDS:
        raise ValueError("manifest fields do not match schema version 1")
    if type(record["schema_version"]) is not int or record["schema_version"] != 1:
        raise ValueError("unsupported schema_version")
    validate_ids(record["session_id"], record["episode_id"])
    config = object_configuration(record["scenario"])
    if record["object_configuration"] != config:
        raise ValueError("object_configuration must match the declared scenario")
    if type(record["object_configuration"].get("unexpected_object")) is not bool:
        raise ValueError("unexpected_object must be a bool")
    for key in ("width", "height", "image_bytes"):
        if type(record[key]) is not int or record[key] <= 0:
            raise ValueError(f"{key} must be a positive integer")
    for key in ("device", "camera_source"):
        if not isinstance(record[key], str) or not record[key].strip():
            raise ValueError(f"{key} must be a nonblank string")
    if record["source_kind"] not in ("camera", "sample"):
        raise ValueError("source_kind must be camera or sample")
    if not isinstance(record["notes"], str):
        raise ValueError("notes must be a string")
    if not isinstance(record["captured_at"], str):
        raise ValueError("captured_at must be an ISO 8601 UTC string")
    try:
        timestamp = datetime.fromisoformat(record["captured_at"])
        normalized = utc_time(timestamp).isoformat()
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid captured_at") from exc
    if record["captured_at"] != normalized:
        raise ValueError("captured_at must be canonical UTC ISO 8601 (+00:00)")
    prefix = record["episode_id"] + "_" + timestamp.strftime("%Y%m%dT%H%M%S%fZ") + "_"
    if not isinstance(record["capture_id"], str) or not re.fullmatch(re.escape(prefix) + r"[0-9a-f]{12}", record["capture_id"]):
        raise ValueError("capture_id must match episode_id, timestamp and generated nonce")
    expected_path = f"{record['session_id']}/{record['episode_id']}/images/{record['capture_id']}.png"
    if record["image_path"] != expected_path:
        raise ValueError("image_path must match the generated relative PNG path")
    if not isinstance(record["image_sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", record["image_sha256"]):
        raise ValueError("invalid image_sha256")


def plain_path(path: Path) -> None:
    """Reject pre-existing symlinks/junctions in the user-selected output path."""
    for part in [*reversed(path.parents), path]:
        if part.is_symlink():
            raise CaptureError(f"Output path contains a symlink: {part}")
        if part.exists() and getattr(part.lstat(), "st_file_attributes", 0) & 0x400:
            raise CaptureError(f"Output path contains a junction/reparse point: {part}")


@contextmanager
def session_lock(session: Path):
    lock_path = session / ".capture.lock"
    plain_path(lock_path)
    try:
        handle = lock_path.open("x", encoding="utf-8")
    except FileExistsError as exc:
        raise CaptureError(f"Session busy or interrupted: {lock_path}; inspect owner before manual recovery") from exc
    try:
        with handle:
            handle.write(f"pid={os.getpid()} device={socket.gethostname()}\n")
            handle.flush()
            yield
    finally:
        lock_path.unlink()


def read_manifest(path: Path) -> list[dict]:
    plain_path(path)
    if not path.exists():
        return []
    records = []
    seen = set()
    episode_settings = {}
    with path.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            if not line.endswith("\n"):
                raise CaptureError(f"Incomplete manifest line: {path}; preserve and inspect before retry")
            try:
                record = json.loads(line)
                validate_record(record)
            except ValueError as exc:
                raise CaptureError(f"Invalid manifest row {line_number} in {path}: {exc}") from exc
            if record["capture_id"] in seen:
                raise CaptureError(f"Duplicate capture_id already in manifest: {path}")
            settings = [record[key] for key in EPISODE_FIELDS]
            episode = record["episode_id"]
            if episode in episode_settings and episode_settings[episode] != settings:
                raise CaptureError(f"Inconsistent metadata within episode {episode}: {path}")
            episode_settings[episode] = settings
            records.append(record)
            seen.add(record["capture_id"])
    return records


def append_manifest(path: Path, record: dict) -> None:
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(record, ensure_ascii=False, allow_nan=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def save_capture(output_root: Path, record: dict, image_png: bytes) -> Path:
    """Exclusive image creation followed by JSONL append, under a session lock.

    On partial I/O failure, keep the new file for manual recovery. No success is
    returned and the next writer rejects orphan files or incomplete manifest rows.
    This is not a cross-file transaction or a distributed filesystem lock.
    """
    validate_record(record)
    if not isinstance(image_png, bytes) or not image_png.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("image_png must contain encoded PNG bytes")
    if len(image_png) != record["image_bytes"] or hashlib.sha256(image_png).hexdigest() != record["image_sha256"]:
        raise ValueError("image bytes do not match metadata")
    root = Path(os.path.abspath(output_root))
    session = root / record["session_id"]
    image_path = root / record["image_path"]
    manifest = session / "manifest.jsonl"
    plain_path(image_path)
    session.mkdir(parents=True, exist_ok=True)
    with session_lock(session):
        records = read_manifest(manifest)
        recorded_paths = set()
        for previous in records:
            if previous["session_id"] != record["session_id"]:
                raise CaptureError("Manifest contains a different session_id")
            previous_path = root / previous["image_path"]
            plain_path(previous_path)
            if not previous_path.is_file() or previous_path.stat().st_size != previous["image_bytes"]:
                raise CaptureError(f"Existing manifest/image mismatch: {previous_path}")
            recorded_paths.add(previous_path)
            if previous["capture_id"] == record["capture_id"]:
                raise CaptureError("Duplicate capture_id; existing image and manifest are preserved")
            if previous["episode_id"] == record["episode_id"]:
                for key in EPISODE_FIELDS:
                    if previous[key] != record[key]:
                        raise CaptureError(f"Episode {key} changed; use a new episode_id")
        existing_images = set(session.glob("*/images/*.png"))
        if existing_images != recorded_paths:
            raise CaptureError(f"Orphan image or manifest mismatch in {session}; inspect before retry")
        image_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with image_path.open("xb") as stream:
                stream.write(image_png)
                stream.flush()
                os.fsync(stream.fileno())
            append_manifest(manifest, record)
        except OSError as exc:
            raise CaptureError(f"Storage failed; preserve and inspect {image_path} and {manifest}: {exc}") from exc
    return image_path


def read_source(args):
    """Dataset-only input selection; no production Camera Protocol implementation."""
    import cv2

    if args.sample is not None:
        frame = cv2.imread(str(args.sample), cv2.IMREAD_COLOR)
        if frame is None:
            raise CaptureError(f"Cannot decode sample image: {args.sample}")
        return frame, datetime.now(timezone.utc), "sample", str(args.sample)
    capture = cv2.VideoCapture(args.camera, cv2.CAP_V4L2)
    try:
        if not capture.isOpened():
            raise CaptureError(f"Cannot open V4L2 camera {args.camera}; check device, permissions and busy processes")
        capture.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*args.fourcc))
        capture.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)
        capture.set(cv2.CAP_PROP_FPS, args.fps)
        # Discard bounded startup frames; never turn these into a burst dataset.
        for _ in range(5):
            ok, frame = capture.read()
            if not ok or frame is None:
                raise CaptureError(f"Frame read failed from {args.camera}")
        timestamp = datetime.now(timezone.utc)
        if frame.shape[:2] != (args.height, args.width):
            raise CaptureError(f"Requested {args.width}x{args.height}, received {frame.shape[1]}x{frame.shape[0]}")
        actual_code = int(capture.get(cv2.CAP_PROP_FOURCC))
        actual_fourcc = "".join(chr((actual_code >> (8 * i)) & 255) for i in range(4))
        print(json.dumps({"backend": capture.getBackendName(), "fourcc": actual_fourcc,
                          "fps_reported": capture.get(cv2.CAP_PROP_FPS)}), file=sys.stderr)
        if actual_fourcc != args.fourcc:
            raise CaptureError(f"Camera negotiated {actual_fourcc!r}, expected {args.fourcc!r}")
        return frame, timestamp, "camera", args.camera
    finally:
        capture.release()


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(description=__doc__)
    command.add_argument("--output-root", type=Path, required=True)
    command.add_argument("--session-id", required=True)
    command.add_argument("--episode-id", required=True)
    command.add_argument("--scenario", choices=SCENARIOS, required=True)
    source = command.add_mutually_exclusive_group(required=True)
    source.add_argument("--camera", help="Verified Linux V4L2 node, for example /dev/video0")
    source.add_argument("--sample", type=Path, help="Existing test image; marked sample, not formal pilot data")
    command.add_argument("--width", type=int, default=640)
    command.add_argument("--height", type=int, default=480)
    command.add_argument("--fourcc", choices=("YUYV", "MJPG"), default="YUYV")
    command.add_argument("--fps", type=int, default=30)
    command.add_argument("--notes", default="")
    return command


def main(argv=None) -> int:
    args = parser().parse_args(argv)
    try:
        import cv2
    except ImportError as exc:
        print(f"CAPTURE_ERROR: OpenCV is required for image acquisition: {exc}", file=sys.stderr)
        return 1
    try:
        validate_ids(args.session_id, args.episode_id)
        if args.width <= 0 or args.height <= 0 or args.fps <= 0:
            raise ValueError("width, height and fps must be positive")
        frame, timestamp, source_kind, source_name = read_source(args)
        ok, encoded = cv2.imencode(".png", frame)
        if not ok:
            raise CaptureError("PNG encoding failed")
        image_png = encoded.tobytes()
        decoded = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
        if decoded is None or decoded.shape[:2] != frame.shape[:2]:
            raise CaptureError("Encoded PNG reload check failed")
        record = make_record(session_id=args.session_id, episode_id=args.episode_id,
                             scenario=args.scenario, captured_at=timestamp,
                             width=int(frame.shape[1]), height=int(frame.shape[0]),
                             device=socket.gethostname(), camera_source=source_name,
                             source_kind=source_kind, image_png=image_png, notes=args.notes)
        output = save_capture(args.output_root, record, image_png)
        print(json.dumps({"status": "saved", "image": str(output), "metadata": record}, ensure_ascii=False))
        return 0
    except (CaptureError, ValueError, OSError, cv2.error) as exc:
        print(f"CAPTURE_ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
