# TASK-017 — Assembly evidence contract

Scope: canonical jetson/; baseline 011a3f46478b02f34b68a34073ac79241975d1e9.
Operating release remains engine-integrated-90a914423826735a.

Acceptance: reproduce the field KeyError using preserved three PNGs and Journal
observations; compute the existing integrity detector at the Worker boundary;
preserve identity/timestamps/quality and both PNG/pixel hashes through Journal;
reject missing or contradictory evidence explicitly; replay the real frozen
assembly models on ARM64 without cameras, PLC sockets or publication; run the
previous 204 related native regressions plus contract tests. Preserve model,
pose/crop, three-frame policy, PLC/EDS, spent approval and all operating data.

Implementation plan:
1. Copy/hash only the named failed inspection into private test evidence.
2. Add failing Worker/Journal/assembly and tampering tests.
3. Add versioned capture integrity metadata and conservative evidence loading.
4. Run PC and bounded ARM64 delta-overlay tests, real saved-frame inference.
5. Review, commit/push intended source/tests/docs; record deployment difference.

No full candidate, no service restart/current replacement, no new field trial.
Final state: STOP_FOR_DEPLOY_APPROVAL. Native scratch is temporary, with outputs
retrieved and verified before exact-path cleanup. Original evidence stays intact.

Verified: actual saved three-frame KeyError reproduced before model call; fixed
Worker/Journal/Assembly contract; PC7/native211 PASS. Real frozen CUDA replay
reached COMPLETE without KeyError, but product detection/preprocessing yielded
REVIEW in all three frames; classifiers not run without valid crops. Final
combination remains REVIEW, never promoted to PASS. Original operating ERROR
record and spent approval retained. Current113/frozen28 hashes verified, no
service restart or extra result. Class1 connection counter7->13 unresolved.

Report: docs/ASSEMBLY_INTEGRITY_CONTRACT_FIX_REPORT.md.
Private evidence: tag_data_link_008/assembly_integrity_017/.
Implementation/isolated verification complete; operating deployment NOT_RUN.
