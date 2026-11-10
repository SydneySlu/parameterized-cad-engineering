# APP-001-V5-ACTIVATION-PREP handoff

To: Codex independent reviewer
Status: review; proposed activation preparation only

Review `prompt-v5.md`, `manifest.json`, `README.md`, `checkpoint.md`, `docs/DECISIONS.md` ADR-0018, and `tests/llm/test_v5_activation_prep.py`.

Focus on source/copy hashes and identity, whether the candidate-to-activation copy changes only version/heading labels, whether v4 is accurately preserved as production and rollback target, whether ADR-0018 cleanly separates strategy acceptance, activation implementation, and formal-run authorization, and whether the offline test actually guards against accidental activation.

Do not change production code or create/authorize a batch. Report blockers, non-blocking suggestions, commands/results, and whether the package is ready for the project owner to review.
