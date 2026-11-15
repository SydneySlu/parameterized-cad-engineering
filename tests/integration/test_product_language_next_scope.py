"""Offline contract tests for the APP-003 next ten-input scope preflight.

All tests use temporary directories and mocks.  No network calls, no
credential reads, no evaluator-labels.json opens, no canonical batch directory
creation, no CAD execution.
"""

from __future__ import annotations

import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from llm.authorization import AuthorizationScopeError
from llm.product_language_next_authorization import (
    PRODUCT_LANGUAGE_NEXT_CONDITION,
    PRODUCT_LANGUAGE_NEXT_INPUT_IDS,
    PRODUCT_LANGUAGE_NEXT_INPUTS_SHA256,
    PRODUCT_LANGUAGE_NEXT_LABELS_SHA256,
    PRODUCT_LANGUAGE_NEXT_MAX_ATTEMPTS_PER_RUN,
    PRODUCT_LANGUAGE_NEXT_MAX_BATCH_HTTP,
    PRODUCT_LANGUAGE_NEXT_MAX_LOGICAL_RUNS,
    PRODUCT_LANGUAGE_NEXT_MODEL,
    PRODUCT_LANGUAGE_NEXT_PROFILE_ID,
    PRODUCT_LANGUAGE_NEXT_PROVIDER,
    ProductLanguageNextApprovalValidationError,
    ProductLanguageNextAuthorization,
    ProductLanguageNextFormalApproval,
    authorize_product_language_next_run,
    make_language_next_test_approval,
    validate_product_language_next_formal_approval_binding,
)
from integration import product_language_next_formal_runner as runner


def _auth(batch_id: str = "next-offline-candidate") -> ProductLanguageNextAuthorization:
    return authorize_product_language_next_run(batch_id=batch_id)


def _real_approval(batch_id: str = "next-offline-candidate") -> ProductLanguageNextFormalApproval:
    return ProductLanguageNextFormalApproval(
        batch_id=batch_id,
        profile_id=PRODUCT_LANGUAGE_NEXT_PROFILE_ID,
        inputs_sha256=PRODUCT_LANGUAGE_NEXT_INPUTS_SHA256,
        evaluator_labels_sha256=PRODUCT_LANGUAGE_NEXT_LABELS_SHA256,
        provider=PRODUCT_LANGUAGE_NEXT_PROVIDER,
        model=PRODUCT_LANGUAGE_NEXT_MODEL,
        condition=PRODUCT_LANGUAGE_NEXT_CONDITION,
        max_batch_http=PRODUCT_LANGUAGE_NEXT_MAX_BATCH_HTTP,
        automatic_cad_pipeline=False,
        approver="Wang sikai",
        approved_at_utc="2026-11-15T10:00:00Z",
        approval_statement=(
            "I approve the formal execution of the next ten-input language "
            "sample batch " + batch_id
        ),
        approval_record_ref="Codex conversation 2026-11-15",
        is_test_only=False,
    )


class TestProductLanguageNextAuthorization(unittest.TestCase):
    def test_profile_binds_ten_n_ids_hashes_provider_and_twenty_http(self) -> None:
        auth = _auth()
        summary = auth.scope_summary()
        self.assertEqual(summary["profile_id"], PRODUCT_LANGUAGE_NEXT_PROFILE_ID)
        self.assertEqual(len(summary["input_ids"]), 10)
        self.assertEqual(summary["inputs_sha256"], PRODUCT_LANGUAGE_NEXT_INPUTS_SHA256)
        self.assertEqual(summary["evaluator_labels_sha256"], PRODUCT_LANGUAGE_NEXT_LABELS_SHA256)
        self.assertEqual(summary["max_batch_http"], 20)
        self.assertTrue(auth.provider_model_is_allowed(summary["provider"], summary["model"]))
        self.assertEqual(auth.max_chat_attempts_for(summary["provider"]), 20)

    def test_profile_id_is_next_not_old(self) -> None:
        auth = _auth()
        self.assertNotEqual(auth.profile_id, "app003-product-language.v1")
        self.assertEqual(auth.profile_id, "app003-product-language-next.v1")

    def test_input_ids_are_n01_through_n10(self) -> None:
        auth = _auth()
        ids = auth.input_ids
        self.assertEqual(len(ids), 10)
        self.assertTrue(all(i.startswith("N") for i in ids))
        self.assertEqual(ids[0], "N01-centimeter-catalog-value")
        self.assertEqual(ids[-1], "N10-derived-width-minimum")

    def test_wrong_profile_rejected(self) -> None:
        with self.assertRaises(AuthorizationScopeError):
            replace(_auth(), profile_id="app003-product-language.v1")

    def test_wrong_inputs_hash_rejected(self) -> None:
        with self.assertRaises(AuthorizationScopeError):
            replace(_auth(), inputs_sha256="0" * 64)

    def test_wrong_labels_hash_rejected(self) -> None:
        with self.assertRaises(AuthorizationScopeError):
            replace(_auth(), evaluator_labels_sha256="0" * 64)

    def test_wrong_provider_rejected(self) -> None:
        with self.assertRaises(AuthorizationScopeError):
            replace(_auth(), providers=frozenset({"Ollama"}))

    def test_wrong_model_rejected(self) -> None:
        with self.assertRaises(AuthorizationScopeError):
            replace(_auth(), models=frozenset({"qwen3:8b"}))

    def test_wrong_condition_rejected(self) -> None:
        with self.assertRaises(AuthorizationScopeError):
            replace(_auth(), conditions=frozenset({"C1"}))

    def test_wrong_budget_rejected(self) -> None:
        with self.assertRaises(AuthorizationScopeError):
            replace(_auth(), max_batch_attempts=99)

    def test_wrong_max_logical_runs_rejected(self) -> None:
        with self.assertRaises(AuthorizationScopeError):
            replace(_auth(), max_logical_runs=99)

    def test_wrong_max_attempts_per_run_rejected(self) -> None:
        with self.assertRaises(AuthorizationScopeError):
            replace(_auth(), max_attempts_per_run=99)

    def test_expected_logical_run_id_format(self) -> None:
        auth = _auth()
        rid = auth.expected_logical_run_id("N01-centimeter-catalog-value")
        self.assertEqual(
            rid,
            "N01-centimeter-catalog-value__C0__DeepSeek__deepseek-flash",
        )

    def test_expected_logical_run_id_rejects_out_of_scope_input(self) -> None:
        auth = _auth()
        with self.assertRaises(AuthorizationScopeError):
            auth.expected_logical_run_id("L01-legal-24mm")


class TestProductLanguageNextApproval(unittest.TestCase):

    def test_valid_real_approval_constructs(self) -> None:
        a = _real_approval()
        self.assertEqual(a.profile_id, PRODUCT_LANGUAGE_NEXT_PROFILE_ID)
        self.assertEqual(a.inputs_sha256, PRODUCT_LANGUAGE_NEXT_INPUTS_SHA256)
        self.assertEqual(a.evaluator_labels_sha256, PRODUCT_LANGUAGE_NEXT_LABELS_SHA256)
        self.assertFalse(a.is_test_only)
        self.assertFalse(a.automatic_cad_pipeline)

    def test_test_only_approval_constructs(self) -> None:
        a = make_language_next_test_approval(batch_id="test-batch")
        self.assertTrue(a.is_test_only)

    def test_wrong_profile_id_rejected(self) -> None:
        with self.assertRaises(ProductLanguageNextApprovalValidationError):
            ProductLanguageNextFormalApproval(
                batch_id="test",
                profile_id="app003-product-language.v1",
                inputs_sha256=PRODUCT_LANGUAGE_NEXT_INPUTS_SHA256,
                evaluator_labels_sha256=PRODUCT_LANGUAGE_NEXT_LABELS_SHA256,
                provider=PRODUCT_LANGUAGE_NEXT_PROVIDER,
                model=PRODUCT_LANGUAGE_NEXT_MODEL,
                condition=PRODUCT_LANGUAGE_NEXT_CONDITION,
                max_batch_http=PRODUCT_LANGUAGE_NEXT_MAX_BATCH_HTTP,
                automatic_cad_pipeline=False,
                approver="X",
                approved_at_utc="2026-11-15T00:00:00Z",
                approval_statement="ok",
            )

    def test_wrong_inputs_hash_rejected(self) -> None:
        with self.assertRaises(ProductLanguageNextApprovalValidationError):
            ProductLanguageNextFormalApproval(
                batch_id="test",
                profile_id=PRODUCT_LANGUAGE_NEXT_PROFILE_ID,
                inputs_sha256="0" * 64,
                evaluator_labels_sha256=PRODUCT_LANGUAGE_NEXT_LABELS_SHA256,
                provider=PRODUCT_LANGUAGE_NEXT_PROVIDER,
                model=PRODUCT_LANGUAGE_NEXT_MODEL,
                condition=PRODUCT_LANGUAGE_NEXT_CONDITION,
                max_batch_http=PRODUCT_LANGUAGE_NEXT_MAX_BATCH_HTTP,
                automatic_cad_pipeline=False,
                approver="X",
                approved_at_utc="2026-11-15T00:00:00Z",
                approval_statement="ok",
            )

    def test_wrong_labels_hash_rejected(self) -> None:
        with self.assertRaises(ProductLanguageNextApprovalValidationError):
            ProductLanguageNextFormalApproval(
                batch_id="test",
                profile_id=PRODUCT_LANGUAGE_NEXT_PROFILE_ID,
                inputs_sha256=PRODUCT_LANGUAGE_NEXT_INPUTS_SHA256,
                evaluator_labels_sha256="0" * 64,
                provider=PRODUCT_LANGUAGE_NEXT_PROVIDER,
                model=PRODUCT_LANGUAGE_NEXT_MODEL,
                condition=PRODUCT_LANGUAGE_NEXT_CONDITION,
                max_batch_http=PRODUCT_LANGUAGE_NEXT_MAX_BATCH_HTTP,
                automatic_cad_pipeline=False,
                approver="X",
                approved_at_utc="2026-11-15T00:00:00Z",
                approval_statement="ok",
            )

    def test_wrong_provider_rejected(self) -> None:
        with self.assertRaises(ProductLanguageNextApprovalValidationError):
            ProductLanguageNextFormalApproval(
                batch_id="test",
                profile_id=PRODUCT_LANGUAGE_NEXT_PROFILE_ID,
                inputs_sha256=PRODUCT_LANGUAGE_NEXT_INPUTS_SHA256,
                evaluator_labels_sha256=PRODUCT_LANGUAGE_NEXT_LABELS_SHA256,
                provider="Ollama",
                model=PRODUCT_LANGUAGE_NEXT_MODEL,
                condition=PRODUCT_LANGUAGE_NEXT_CONDITION,
                max_batch_http=PRODUCT_LANGUAGE_NEXT_MAX_BATCH_HTTP,
                automatic_cad_pipeline=False,
                approver="X",
                approved_at_utc="2026-11-15T00:00:00Z",
                approval_statement="ok",
            )

    def test_wrong_model_rejected(self) -> None:
        with self.assertRaises(ProductLanguageNextApprovalValidationError):
            ProductLanguageNextFormalApproval(
                batch_id="test",
                profile_id=PRODUCT_LANGUAGE_NEXT_PROFILE_ID,
                inputs_sha256=PRODUCT_LANGUAGE_NEXT_INPUTS_SHA256,
                evaluator_labels_sha256=PRODUCT_LANGUAGE_NEXT_LABELS_SHA256,
                provider=PRODUCT_LANGUAGE_NEXT_PROVIDER,
                model="qwen3:8b",
                condition=PRODUCT_LANGUAGE_NEXT_CONDITION,
                max_batch_http=PRODUCT_LANGUAGE_NEXT_MAX_BATCH_HTTP,
                automatic_cad_pipeline=False,
                approver="X",
                approved_at_utc="2026-11-15T00:00:00Z",
                approval_statement="ok",
            )

    def test_wrong_condition_rejected(self) -> None:
        with self.assertRaises(ProductLanguageNextApprovalValidationError):
            ProductLanguageNextFormalApproval(
                batch_id="test",
                profile_id=PRODUCT_LANGUAGE_NEXT_PROFILE_ID,
                inputs_sha256=PRODUCT_LANGUAGE_NEXT_INPUTS_SHA256,
                evaluator_labels_sha256=PRODUCT_LANGUAGE_NEXT_LABELS_SHA256,
                provider=PRODUCT_LANGUAGE_NEXT_PROVIDER,
                model=PRODUCT_LANGUAGE_NEXT_MODEL,
                condition="C1",
                max_batch_http=PRODUCT_LANGUAGE_NEXT_MAX_BATCH_HTTP,
                automatic_cad_pipeline=False,
                approver="X",
                approved_at_utc="2026-11-15T00:00:00Z",
                approval_statement="ok",
            )

    def test_automatic_cad_pipeline_true_rejected(self) -> None:
        with self.assertRaises(ProductLanguageNextApprovalValidationError):
            ProductLanguageNextFormalApproval(
                batch_id="test",
                profile_id=PRODUCT_LANGUAGE_NEXT_PROFILE_ID,
                inputs_sha256=PRODUCT_LANGUAGE_NEXT_INPUTS_SHA256,
                evaluator_labels_sha256=PRODUCT_LANGUAGE_NEXT_LABELS_SHA256,
                provider=PRODUCT_LANGUAGE_NEXT_PROVIDER,
                model=PRODUCT_LANGUAGE_NEXT_MODEL,
                condition=PRODUCT_LANGUAGE_NEXT_CONDITION,
                max_batch_http=PRODUCT_LANGUAGE_NEXT_MAX_BATCH_HTTP,
                automatic_cad_pipeline=True,
                approver="X",
                approved_at_utc="2026-11-15T00:00:00Z",
                approval_statement="ok",
            )

    def test_empty_approver_rejected(self) -> None:
        with self.assertRaises(ProductLanguageNextApprovalValidationError):
            ProductLanguageNextFormalApproval(
                batch_id="test",
                profile_id=PRODUCT_LANGUAGE_NEXT_PROFILE_ID,
                inputs_sha256=PRODUCT_LANGUAGE_NEXT_INPUTS_SHA256,
                evaluator_labels_sha256=PRODUCT_LANGUAGE_NEXT_LABELS_SHA256,
                provider=PRODUCT_LANGUAGE_NEXT_PROVIDER,
                model=PRODUCT_LANGUAGE_NEXT_MODEL,
                condition=PRODUCT_LANGUAGE_NEXT_CONDITION,
                max_batch_http=PRODUCT_LANGUAGE_NEXT_MAX_BATCH_HTTP,
                automatic_cad_pipeline=False,
                approver="   ",
                approved_at_utc="2026-11-15T00:00:00Z",
                approval_statement="ok",
            )

    def test_as_audit_dict_contains_no_secret_fields(self) -> None:
        d = _real_approval().as_audit_dict()
        for key in d:
            self.assertNotIn("key", key.lower())
            self.assertNotIn("token", key.lower())
            self.assertNotIn("secret", key.lower())


class TestValidateNextApprovalBinding(unittest.TestCase):

    def test_matching_non_test_approval_passes(self) -> None:
        validate_product_language_next_formal_approval_binding(
            _auth(), _real_approval()
        )

    def test_test_only_approval_rejected(self) -> None:
        with self.assertRaises(ProductLanguageNextApprovalValidationError):
            validate_product_language_next_formal_approval_binding(
                _auth(), make_language_next_test_approval(batch_id="next-offline-candidate")
            )

    def test_batch_id_mismatch_rejected(self) -> None:
        with self.assertRaises(ProductLanguageNextApprovalValidationError):
            validate_product_language_next_formal_approval_binding(
                _auth("batch-A"), _real_approval("batch-B")
            )

    def test_wrong_authorization_type_rejected(self) -> None:
        with self.assertRaises(ProductLanguageNextApprovalValidationError):
            validate_product_language_next_formal_approval_binding(
                object(),  # type: ignore
                _real_approval(),
            )

    def test_wrong_approval_type_rejected(self) -> None:
        with self.assertRaises(ProductLanguageNextApprovalValidationError):
            validate_product_language_next_formal_approval_binding(
                _auth(), object()  # type: ignore
            )


class TestProductLanguageNextOfflinePreflight(unittest.TestCase):

    def test_valid_preflight_plans_ten_runs_and_twenty_http(self) -> None:
        result = runner.run_language_next_offline_preflight(_auth())
        self.assertTrue(result["ok"], result["errors"])
        self.assertEqual(len(result["planned_runs"]), 10)
        self.assertEqual(result["details"]["budget_plan"]["computed_max_http"], 20)
        self.assertEqual(result["details"]["budget_plan"]["authorized_max_http"], 20)
        self.assertEqual(result["details"]["profile_id"], PRODUCT_LANGUAGE_NEXT_PROFILE_ID)

    def test_input_hash_failure_fails_closed(self) -> None:
        with patch.object(runner, "_load_next_inputs", side_effect=ValueError("hash mismatch")):
            result = runner.run_language_next_offline_preflight(_auth())
        self.assertFalse(result["ok"])
        self.assertIn("inputs_check:ValueError", result["errors"])
        self.assertEqual(result["planned_runs"], [])

    def test_existing_batch_directory_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            batch_dir = Path(temp) / "already-there"
            batch_dir.mkdir()
            result = runner.run_language_next_offline_preflight(
                _auth(), batch_dir=batch_dir
            )
        self.assertFalse(result["ok"])
        self.assertIn("batch_directory_already_exists", result["errors"])

    def test_labels_file_is_never_opened_and_no_credentials_or_network(self) -> None:
        original_read_bytes = Path.read_bytes

        def guarded_read_bytes(path: Path) -> bytes:
            self.assertNotEqual(path.name, "evaluator-labels.json")
            return original_read_bytes(path)

        with (
            patch.object(Path, "read_bytes", guarded_read_bytes),
            patch("urllib.request.urlopen") as urlopen,
            patch("llm.env_loader.load_deepseek_environment") as load_env,
        ):
            result = runner.run_language_next_offline_preflight(_auth())
        self.assertTrue(result["ok"], result["errors"])
        urlopen.assert_not_called()
        load_env.assert_not_called()

    def test_wrong_authorization_type_rejected(self) -> None:
        with self.assertRaises(AuthorizationScopeError):
            runner.run_language_next_offline_preflight(object())  # type: ignore[arg-type]

    def test_planned_run_ids_use_n_prefix(self) -> None:
        result = runner.run_language_next_offline_preflight(_auth())
        self.assertTrue(result["ok"])
        for run in result["planned_runs"]:
            self.assertTrue(run["input_id"].startswith("N"),
                            f"expected N-prefix, got {run['input_id']}")

    def test_formal_evaluation_allowed_is_false(self) -> None:
        result = runner.run_language_next_offline_preflight(_auth())
        self.assertFalse(result["details"]["formal_evaluation_allowed"])

    def test_evaluator_labels_not_opened_flag(self) -> None:
        result = runner.run_language_next_offline_preflight(_auth())
        self.assertFalse(result["details"]["evaluator_labels_opened"])

    def test_budget_constants_match_requirements(self) -> None:
        self.assertEqual(PRODUCT_LANGUAGE_NEXT_MAX_LOGICAL_RUNS, 10)
        self.assertEqual(PRODUCT_LANGUAGE_NEXT_MAX_ATTEMPTS_PER_RUN, 2)
        self.assertEqual(PRODUCT_LANGUAGE_NEXT_MAX_BATCH_HTTP, 20)
        self.assertEqual(
            PRODUCT_LANGUAGE_NEXT_MAX_LOGICAL_RUNS * PRODUCT_LANGUAGE_NEXT_MAX_ATTEMPTS_PER_RUN,
            PRODUCT_LANGUAGE_NEXT_MAX_BATCH_HTTP,
        )


if __name__ == "__main__":
    unittest.main()
