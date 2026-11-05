"""Tests for src/llm/authorization.py — formal run authorization scope validation.

Tests 2 (gate refusal for wrong scope), plus basic authorization construction.
No real network calls.  No environment variable reads.
"""

import unittest

from src.llm.authorization import (
    AuthorizationScopeError,
    FormalRunAuthorization,
    _FROZEN_CONDITIONS,
    _FROZEN_MAX_BATCH_ATTEMPTS,
    _FROZEN_MAX_LOGICAL_RUNS,
    _FROZEN_MAX_PROVIDER_ATTEMPTS,
    _FROZEN_MAX_ATTEMPTS_PER_RUN,
    _FROZEN_MODELS,
    _FROZEN_PROTOCOL_VERSIONS,
    _FROZEN_PROVIDERS,
    _FROZEN_SAMPLE_SET,
    _valid_kwargs,
    authorize_phase1_run,
)
from src.llm.contract import (
    ACCEPTANCE_SET_VERSION,
    CONTRACT_VERSION,
    DEEPSEEK_MODEL,
    DEEPSEEK_PROVIDER,
    OLLAMA_MODEL,
    OLLAMA_PROVIDER,
    PROMPT_VERSION,
)


class AuthorizationConstructionTests(unittest.TestCase):
    def test_valid_construction_succeeds(self):
        auth = FormalRunAuthorization(**_valid_kwargs())
        self.assertEqual(auth.batch_id, "test-batch-001")
        self.assertEqual(auth.max_logical_runs, 36)

    def test_authorize_phase1_run_factory(self):
        auth = authorize_phase1_run(batch_id="batch-xyz")
        self.assertEqual(auth.batch_id, "batch-xyz")
        self.assertEqual(auth.max_batch_attempts, 108)
        self.assertEqual(auth.max_provider_attempts, 54)
        self.assertIn("C0", auth.conditions)
        self.assertIn("C1", auth.conditions)

    def test_scope_hash_is_64_hex(self):
        auth = authorize_phase1_run(batch_id="batch-001")
        h = auth.scope_hash()
        self.assertEqual(len(h), 64)
        self.assertRegex(h, r"^[0-9a-f]{64}$")

    def test_scope_hash_stable(self):
        a = authorize_phase1_run(batch_id="x")
        b = authorize_phase1_run(batch_id="x")
        self.assertEqual(a.scope_hash(), b.scope_hash())

    def test_scope_hash_differs_with_batch_id(self):
        a = authorize_phase1_run(batch_id="batch-1")
        b = authorize_phase1_run(batch_id="batch-2")
        self.assertNotEqual(a.scope_hash(), b.scope_hash())

    def test_scope_summary_no_secrets(self):
        auth = authorize_phase1_run(batch_id="test")
        summary = auth.scope_summary()
        summary_str = str(summary)
        self.assertNotIn("DEEPSEEK_API_KEY", summary_str)
        self.assertNotIn("Bearer", summary_str)
        self.assertNotIn("sk-", summary_str)

    def test_provider_model_allowed(self):
        auth = authorize_phase1_run(batch_id="x")
        self.assertTrue(auth.provider_model_is_allowed(DEEPSEEK_PROVIDER, DEEPSEEK_MODEL))
        self.assertTrue(auth.provider_model_is_allowed(OLLAMA_PROVIDER, OLLAMA_MODEL))
        self.assertFalse(auth.provider_model_is_allowed("SomeOther", "model-x"))


class AuthorizationScopeRejectionTests(unittest.TestCase):
    """Test 2: gate refused when authorization scope does not match."""

    def test_wrong_protocol_version_rejected(self):
        with self.assertRaises(AuthorizationScopeError):
            FormalRunAuthorization(
                **_valid_kwargs(protocol_versions=frozenset({"wrong.v0"}))
            )

    def test_wrong_sample_set_rejected(self):
        with self.assertRaises(AuthorizationScopeError):
            FormalRunAuthorization(**_valid_kwargs(sample_set="acceptance-set-wrong"))

    def test_c2_condition_rejected(self):
        """Scope with C2 instead of C0/C1 must be rejected."""
        with self.assertRaises(AuthorizationScopeError):
            FormalRunAuthorization(
                **_valid_kwargs(conditions=frozenset({"C0", "C1", "C2"}))
            )

    def test_only_c2_rejected(self):
        with self.assertRaises(AuthorizationScopeError):
            FormalRunAuthorization(**_valid_kwargs(conditions=frozenset({"C2"})))

    def test_wrong_model_rejected(self):
        with self.assertRaises(AuthorizationScopeError):
            FormalRunAuthorization(
                **_valid_kwargs(models=frozenset({"gpt-4o", OLLAMA_MODEL}))
            )

    def test_wrong_provider_rejected(self):
        with self.assertRaises(AuthorizationScopeError):
            FormalRunAuthorization(
                **_valid_kwargs(providers=frozenset({"OpenAI", OLLAMA_PROVIDER}))
            )

    def test_too_many_logical_runs_rejected(self):
        with self.assertRaises(AuthorizationScopeError):
            FormalRunAuthorization(**_valid_kwargs(max_logical_runs=100))

    def test_too_many_batch_attempts_rejected(self):
        with self.assertRaises(AuthorizationScopeError):
            FormalRunAuthorization(**_valid_kwargs(max_batch_attempts=999))

    def test_ir_cad_not_disabled_rejected(self):
        with self.assertRaises(AuthorizationScopeError):
            FormalRunAuthorization(**_valid_kwargs(ir_cad_geometry_step_disabled=False))

    def test_empty_batch_id_rejected(self):
        with self.assertRaises(AuthorizationScopeError):
            FormalRunAuthorization(**_valid_kwargs(batch_id=""))

    def test_extra_provider_rejected(self):
        """Adding a third provider is not in scope."""
        with self.assertRaises(AuthorizationScopeError):
            FormalRunAuthorization(
                **_valid_kwargs(
                    providers=frozenset({DEEPSEEK_PROVIDER, OLLAMA_PROVIDER, "Anthropic"})
                )
            )


if __name__ == "__main__":
    unittest.main()
