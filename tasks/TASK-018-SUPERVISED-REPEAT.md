# TASK-018 — Supervised repeat inspection
Status: ISOLATED_PASS / STOP_FOR_DEPLOY_APPROVAL. Actual field trials NOT_RUN.
Baseline: fa77a206e35923e6287924e014323bf9c10b8420.
Operating release remains engine-integrated-90a914423826735a.

Approved outcome: SUPERVISED_REPEAT_TEST permits one new physical START/request
per explicit operator preparation. Existing FIRST_PRODUCT_ONLY remains one-shot.
No automatic CLEAR, counter/ledger reset, model/EDS/Assembly/PLC change.

Implementation:
1. C: opt-in supervised admission, new IPC v3 command, immutable used-ID history,
   fully consumed previous request required; same Result-only then Done packets.
2. Python: reuse private approval ledger, add supervised evidence and fresh
   challenges; durable completion + clean stopped snapshot + operator confirmations.
   New tracking session/cycle and source-time cutoff only on accepted preparation.
3. Existing HMI: supervised status, actual AI vs PLC disposition, saved evidence.
   One authenticated same-origin prepare POST; all other mutation routes blocked.
   Per-service private pairing secret, no secret in logs/GET/query. No web START.
4. Focused Python/C and simulated IPC multi-cycle tests; prior regression; ARM64
   isolated build/test. No new full Candidate. Evidence in supervised_repeat_018.
5. Review, commit/push canonical source/tests/docs. Preserve uncommitted user work.
6. Prepare exact deployment/rollback plan; STOP_FOR_DEPLOY_APPROVAL. New explicit
   field-stop/deployment and three-product supervised trial approvals required.

Acceptance: 3 distinct cycle/request/inspection identities, PASS/FAIL/REVIEW/ERROR
each eligible for a NEW approved trial after completion; no implicit admission
from lingering HIGH, output residue, duplicate/stale grant/result, STOP/EStop,
link loss, service restart. Journal integrity/storage/camera faults block.
Operator product-clear confirmation is separate evidence, never AI Area CLEAR.
Track identity is the existing (tracking session, local track ID) pair.

Verification: native C pure-state tests, real AF_UNIX IPC fixture (no AF_INET,
PLC or camera), Python durable Journal and HTTP authorization tests, browser
fixture inspection. Read-only operating state/counters/hashes before and after.
Class1 reconnects counted separately; no timeout/lease changes.

Reuse: Human Gates knowledge ADAPT — one explicit product permission instead of
repeated developer commands, with fresh live context and durable spent IDs.


Verified: ARM64 regression228 + added deadline ERROR repeat1 =229 PASS; C initial22 and supervised sanitizer PASS; local browser PASS. Report: docs/SUPERVISED_REPEAT_INSPECTION_REPORT.md. Prepared release engine-supervised-c6f5b94e8adb4e2e; operating release unchanged. Native evidence/backup verified on notebook.
