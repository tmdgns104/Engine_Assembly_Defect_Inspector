Task ID: V0-T19
Title: Benchmark
Status: TODO
Depends On: V0-T18

## Purpose
Measure runtime and end-to-end performance after deployment packaging.

## Allowed Changes
- Benchmark ONNX inference on Jetson.
- Benchmark TensorRT inference only if rehearse completed.
- Record latency, FPS, memory, and startup timing.

## Forbidden Changes
- Do not compare across different sample sets without noting it.
- Do not treat one-shot numbers as guarantees.

## Verification
- Benchmark report includes both config and environment details.

## PASS Criteria
- Performance results support V1 planning and V0 regression checks.

## Artifacts
- `benchmark_report.md`
