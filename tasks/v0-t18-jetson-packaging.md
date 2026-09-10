Task ID: V0-T18
Title: Jetson Packaging / Startup
Status: TODO
Depends On: V0-T17

## Purpose
Prepare reproducible deployment package for V0 runtime only.

## Allowed Changes
- Create startup and readiness checks.
- Keep runtime-only manifest and version metadata.

## Forbidden Changes
- Do not include training datasets, TensorBoard logs, or large experiment artifacts in runtime package.

## Implementation
- Define package structure and startup script path.
- Validate clean start from cold boot.

## Verification
- Startup passes in fresh environment.

## PASS Criteria
- Packaging is repeatable and minimal.

## Artifacts
- `deployment/manifest.json`
- `startup_guide.md`
