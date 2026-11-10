# APP-001-V5-PROMPT-CANDIDATE handoff

From: Codex hub preparation
To: Codex independent reviewer
Status: review; offline candidate only

Read `checkpoint.md` and `strategy.md` before review. The candidate prompt is `prompt-v5-candidate.md`; it is not loaded by production. Candidate checker changes are isolated to `decision_policy_v5_candidate.py`.

## Review focus

1. Confirm the nine-key `app001-io.v1` envelope and `app001-extraction.v5-candidate` identity are self-consistent and not activated.
2. Check the new MUST-answer rule applies only to complete, conflict-free explicit user claims, while missing bore, non-catalog bore, unsupported requests, coupled-field conflicts, and `second_screw` rule conflicts remain ask/refuse paths.
3. Confirm retrieval is only reference context, not user intent or evidence for user claims.
4. Check P2 consistency rules and checker/test mapping for every catalog-coupled field against `CATALOG_ROWS`.
5. Confirm frozen v4 and acceptance-set hashes, production v4 loader/constants, formal gate, old-batch immutability, and no model/key activity.
6. Treat passing offline tests as deterministic artifact/checker evidence only, not model-effect evidence.

## Evidence

See `checkpoint.md` for commands, results, normal/failure cases, hashes, production boundaries, and known semantic limits. No formal batch is authorized by this handoff.
