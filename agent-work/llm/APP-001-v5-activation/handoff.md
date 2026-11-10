# APP-001-V5-ACTIVATION handoff

To: Codex central independent review

Review this activation as a separate versioned switch under accepted ADR-0018. Verify the diff and current branch/HEAD; run `tests.llm.test_v5_activation`, v5 candidate/preparation checks, relevant parser/adapter regressions, then LLM and Schema suites under Python 3.11.18. Check v5 prompt SHA-256 against both manifest and loader; v4 rollback hash against the archived file; default parser accepts v5 and rejects v4; explicit v4 audit accepts v4; formal gate remains false; no model or credential access occurred.

Do not authorize or run a formal batch. Report blockers, validation commands/results, skips, branch/commit state, and whether the activation is ready to merge.
