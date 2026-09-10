Task ID: V0-T04
Title: Proxy Inspection Dataset Plan + Capture Tool
Status: BLOCKED / WINDOWS_TOOL_READY
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
- Do not mark DONE while plan approval/formal data readiness remains unresolved.

## Verification
- Capture protocol is executable and repeatable.
- Metadata schema is suitable for later grouping.

## PASS Criteria
- Proxy capture plan approved.
- Dataset capture tool requirements finalized.

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

## Result / checkpoint

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
