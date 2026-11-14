"""Offline contract tests for the APP-003 ten-input scope preflight."""

from __future__ import annotations

import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from llm.authorization import AuthorizationScopeError
from llm.product_language_authorization import (
    PRODUCT_LANGUAGE_INPUTS_SHA256,
    PRODUCT_LANGUAGE_LABELS_SHA256,
    PRODUCT_LANGUAGE_MAX_BATCH_HTTP,
    PRODUCT_LANGUAGE_PROFILE_ID,
    ProductLanguageAuthorization,
    authorize_product_language_run,
)
from integration import product_language_runner as runner


def _auth(batch_id: str = "offline-candidate") -> ProductLanguageAuthorization:
    return authorize_product_language_run(batch_id=batch_id)


class TestProductLanguageAuthorization(unittest.TestCase):
    def test_profile_binds_ten_ids_hashes_provider_and_twenty_http(self) -> None:
        auth = _auth()
        summary = auth.scope_summary()
        self.assertEqual(summary["profile_id"], PRODUCT_LANGUAGE_PROFILE_ID)
        self.assertEqual(len(summary["input_ids"]), 10)
        self.assertEqual(summary["inputs_sha256"], PRODUCT_LANGUAGE_INPUTS_SHA256)
        self.assertEqual(summary["evaluator_labels_sha256"], PRODUCT_LANGUAGE_LABELS_SHA256)
        self.assertEqual(summary["max_batch_http"], 20)
        self.assertTrue(auth.provider_model_is_allowed(summary["provider"], summary["model"]))
        self.assertEqual(auth.max_chat_attempts_for(summary["provider"]), 2)

    def test_wrong_profile_or_hash_is_rejected(self) -> None:
        with self.assertRaises(AuthorizationScopeError):
            replace(_auth(), profile_id="app003-product-live.v1")
        with self.assertRaises(AuthorizationScopeError):
            replace(_auth(), inputs_sha256="0" * 64)
        with self.assertRaises(AuthorizationScopeError):
            replace(_auth(), evaluator_labels_sha256="0" * 64)


class TestProductLanguageOfflinePreflight(unittest.TestCase):
    def test_valid_preflight_plans_ten_runs_and_twenty_http(self) -> None:
        result = runner.run_product_language_offline_preflight(_auth())
        self.assertTrue(result["ok"], result["errors"])
        self.assertEqual(len(result["planned_runs"]), 10)
        self.assertEqual(result["details"]["budget_plan"]["computed_max_http"], 20)
        self.assertEqual(result["details"]["budget_plan"]["authorized_max_http"], 20)
        self.assertFalse(result["details"]["execution_enabled"])
        self.assertEqual(result["details"]["profile_id"], PRODUCT_LANGUAGE_PROFILE_ID)

    def test_input_hash_failure_fails_closed(self) -> None:
        with patch.object(runner, "_load_inputs", side_effect=ValueError("hash mismatch")):
            result = runner.run_product_language_offline_preflight(_auth())
        self.assertFalse(result["ok"])
        self.assertIn("inputs_check:ValueError", result["errors"])
        self.assertEqual(result["planned_runs"], [])

    def test_existing_batch_directory_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            batch_dir = Path(temp) / "already-there"
            batch_dir.mkdir()
            result = runner.run_product_language_offline_preflight(
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
            result = runner.run_product_language_offline_preflight(_auth())
        self.assertTrue(result["ok"], result["errors"])
        urlopen.assert_not_called()
        load_env.assert_not_called()

    def test_execution_api_is_explicitly_unavailable(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "offline-preflight-only"):
            runner.run_product_language_batch(authorization=_auth())

    def test_wrong_authorization_type_rejected(self) -> None:
        with self.assertRaises(AuthorizationScopeError):
            runner.run_product_language_offline_preflight(object())  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
