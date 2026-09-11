Task ID: V0-T04
Title: Proxy Inspection Dataset Plan + Capture Tool
Status: DONE / VERIFIED
Depends On: V0-T03

## Purpose
Define a manageable pilot proxy dataset workflow so the user learns capture, label, split, train, tune, and evaluate cycles.

## Allowed Changes
- Implement a standalone dataset capture CLI and Windows tests; preserve production contracts.
- Validate existing Jetson USB/V4L2 input through headless smoke captures only.
- Create capture/session templates.
- Define object names using ordinary placeholders (e.g., `OBJ_A`, `OBJ_B`, `OBJ_C`).
- Include scenario coverage: normal arrangement, missing one required object, missing another required object, extra object, position shift, occlusion, blur, poor exposure.
- Define pilot size based on sessions and scenarios (manageable first pass).

## Forbidden Changes
- Do not hardcode engine part names or final V1 dataset rules.

## Implementation
- `proxy_capture_plan.md`, `session-template.md`, collection metadata fields.
- One capture per command, UTC timestamp, session/episode grouping, PNG plus JSONL,
  exclusive creation and explicit storage errors. Sample input supports device-free tests.
- Windows is the source of truth; only minimal capture files go to a unique Jetson directory.
- No labeling, splitting, training, runtime adapters or network/system package changes.

## Current execution contract

- Baseline: `89d1ab0`, initially clean and matching origin/master.
- Verify: Windows unittest suite + existing T02/T03 preservation + Git exclusions;
  Jetson read-only device/formats check + 3 headless smoke images + reload/hash linkage.
- Human gate: stop before formal Pilot capture; object choice/placement is a human action.
- FINALIZE baseline: `6363f80`. User explicitly accepted the plan/tool/metadata/hardware-path scope as complete; formal Dataset collection is the separate HUMAN-CAPTURE-001 operational gate.
- Hardware evidence is USER-EXECUTED / VERIFIED, supplied by the user; FINALIZE performs no additional Jetson execution. Preserve the distinction from Windows tests and synthetic samples.

## Verification
- Capture protocol is executable and repeatable.
- Metadata schema is suitable for later grouping.

## PASS Criteria
- Proxy capture plan approved.
- Dataset capture tool requirements finalized.
- Windows contract/capture tests pass and Jetson hardware smoke saves/reloads 3 images with metadata/hash verification.
- Formal Pilot count and required human selection/placement remain explicit; T05 is not automatically started.

## Artifacts
- `training/datasets/proxy/proxy_capture_plan.md`
- `training/datasets/proxy/session-template.json`
- `training/datasets/proxy/capture-schema.json`
- `training/datasets/proxy/README.md`
- `training/scripts/capture_proxy.py`
- `training/scripts/verify_proxy_captures.py`
- `tests/test_proxy_capture.py`
- `docs/learning-notes/V0-T04.md`
- `docs/verification/V0-T04.txt`
- `docs/verification/V0-T04-hardware.json`

## Earlier checkpoint (preserved history, superseded by final result below)

- Windows Tool Ready: standalone one-shot capture and read-only session verifier implemented.
- Verification: 40/40 unittest PASS (19 existing contracts + 21 capture tests),
  3 synthetic Windows sample captures reloaded with matching metadata/size/SHA256.
- JSON schema parses and matches field/scenario inventory; executable validator enforces
  cross-field identity, UTC, scenario and episode invariants. No new schema dependency.
- Raw/sample images and raw metadata excluded by Git. T02/T03 protected files and
  existing venv/package versions unchanged. No production Camera/Detector implementation.
- Jetson SSH server reached through the existing target, but BatchMode authentication
  returned Permission denied (publickey,password). No password validity conclusion.
- Jetson hostname/Python/OpenCV, current camera node/formats, 3 hardware smoke captures,
  reload/hash validation and camera release remain UNVERIFIED. No files copied to Jetson.
- No system packages or network settings changed. No labeling, split or training.
- Pilot proposal: 3 sessions x 9 scenarios x 3 physical-placement episodes x 1 capture = 81.
- Human approval of capture plan and actual object selection/placement remain pending.
- Resume: establish existing SSH authentication, inspect hardware read-only, SCP only
  the two scripts to a fresh directory, run 3 CAMERA_SMOKE captures and verify them.
  Then stop as READY_FOR_HUMAN_CAPTURE before formal object capture.
- T04 is not DONE. T05 remains TODO and is not the next executable task yet.

## Final result — V0-T04-FINALIZE

- DONE / VERIFIED: user accepted the plan and completed the hardware smoke using the existing two scripts transferred from Windows. No capture implementation changes during FINALIZE.
- USER-EXECUTED / VERIFIED: jetson-07, Python 3.10.12, OpenCV 4.8.0; HCAM0 via uvcvideo, final node /dev/video0, YUYV 640x480, configured 22 FPS.
- V4L2 30-frame stream exit 0; OpenCV opened=True/backend=V4L2 and 5/5 frame reads. HW_SMOKE01 / HW_SMOKE01_CAMERA_01 / CAMERA_SMOKE saved 3 PNGs; verifier status=verified, captures=3, metadata/reload/SHA256 all PASS.
- User identified USB camera physical disconnection as the root cause of the camera failures. Reconnection enumerated /dev/video0. Do not reinterpret the earlier successful /dev/video2 stream as a failure or assume a structural OpenCV/backend defect. Those later failure logs were not supplied to this repository; retain prior available evidence and attribute the root-cause correction to the user.
- Windows final verification: run the existing complete 40-test suite and audit raw/binary exclusions. Evidence is retained in docs/verification/V0-T04.txt.
- No Jetson execution, system package/network changes, labeling, split or training during FINALIZE.
- Formal Proxy Pilot: NOT STARTED, 0/81 images. CAMERA_SMOKE 3 images are excluded. Human Object Selection and Placement: REQUIRED.
- Next: HUMAN-CAPTURE-001. Human selects OBJ_A/B/C; start S001 with one NORMAL episode, inspect quality, then one MISSING_A episode and inspect again. Expand only after human review. V0-T05 stays TODO / NOT STARTED.
