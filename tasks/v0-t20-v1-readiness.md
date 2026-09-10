Task ID: V0-T20
Title: V0 Final Review / V1 Readiness
Status: TODO
Depends On: V0-T19

## Purpose
Validate V0 completion before moving to asset replacement work.

## Required Completion Definition
1. V0 ML environment setup
2. Proxy dataset capture
3. Labeling
4. Grouped split
5. Baseline training
6. Tuning
7. Validation/Test distinction
8. Final evaluation
9. ONNX export
10. Runtime detector integration
11. Recipe/Decision logic
12. Evidence persistence
13. Web HMI
14. Mock PLC/manual request
15. Jetson camera E2E
16. Failure/recovery tests
17. Deployment packaging
18. Benchmark
19. TensorRT rehearsal (if feasible)
20. V1 readiness review

## V1 Boundary Notes
- V1 starts from a small pilot (around 120 images) and should remain a starting point, not a final target.
- Pilot cycle: capture -> baseline -> error analysis -> targeted capture -> dataset revision -> retrain.
- Keep grouped split by physical unit / episode / session.

## V2 Boundary Notes
- V2 begins after V0/V1 are independently demonstrated.
- V2 adds real PLC/sensor/conveyor control integration only via adapter replacement.

## Verification
- Task map is consistent and no obsolete filename references remain.
- All evidence references resolve.

## PASS Criteria
- `V1-Pilot Review` checklist complete and reviewed.
- Risk register and next-step plan are explicit.

## Artifacts
- `v0-readiness-summary.md`
- `v1-readiness-checklist.md`
