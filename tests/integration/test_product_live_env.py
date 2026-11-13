"""Offline tests for the product-live credential loading boundary."""

from __future__ import annotations

import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from llm.env_loader import (
    EnvironmentConfigurationError,
    load_deepseek_environment,
    load_required_environment,
)
from llm.product_live_authorization import (
    PRODUCT_CONDITION,
    PRODUCT_INPUTS_SHA256,
    PRODUCT_LABELS_SHA256,
    PRODUCT_MAX_BATCH_HTTP,
    PRODUCT_MODEL,
    PRODUCT_PROFILE_ID,
    PRODUCT_PROVIDER,
    ProductLiveFormalApproval,
    authorize_product_live_run,
)
from integration.product_live_runner import (
    ProductLiveConfigurationError,
    run_product_batch,
)


class TestProductLiveEnvironmentLoader(unittest.TestCase):
    def test_loads_key_from_dotenv_without_printing_value(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".env").write_text(
                "# comment\nexport DEEPSEEK_API_KEY='secret-value'\n",
                encoding="utf-8",
            )
            env: dict[str, str] = {}
            captured = io.StringIO()
            with contextlib.redirect_stdout(captured), contextlib.redirect_stderr(captured):
                names = load_deepseek_environment(repo_root=root, environ=env)
            self.assertEqual(names, ("DEEPSEEK_API_KEY",))
            self.assertEqual(env["DEEPSEEK_API_KEY"], "secret-value")
            self.assertNotIn("secret-value", captured.getvalue())

    def test_nonempty_process_value_wins(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".env").write_text("DEEPSEEK_API_KEY=dotenv-value\n", encoding="utf-8")
            env = {"DEEPSEEK_API_KEY": "process-value"}
            load_deepseek_environment(repo_root=root, environ=env)
            self.assertEqual(env["DEEPSEEK_API_KEY"], "process-value")

    def test_empty_process_value_can_be_filled_from_dotenv(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".env").write_text("DEEPSEEK_API_KEY=dotenv-value\n", encoding="utf-8")
            env = {"DEEPSEEK_API_KEY": ""}
            load_deepseek_environment(repo_root=root, environ=env)
            self.assertEqual(env["DEEPSEEK_API_KEY"], "dotenv-value")

    def test_missing_file_fails_when_process_value_is_absent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(EnvironmentConfigurationError) as ctx:
                load_deepseek_environment(repo_root=Path(tmp), environ={})
            self.assertIn("DEEPSEEK_API_KEY", str(ctx.exception))

    def test_empty_dotenv_value_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".env").write_text("DEEPSEEK_API_KEY=   \n", encoding="utf-8")
            with self.assertRaises(EnvironmentConfigurationError):
                load_deepseek_environment(repo_root=root, environ={})

    def test_loader_does_not_mutate_unrelated_environment(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".env").write_text("OTHER=value\n", encoding="utf-8")
            env = {"KEEP": "yes"}
            with self.assertRaises(EnvironmentConfigurationError):
                load_required_environment(
                    dotenv_path=root / ".env",
                    required_keys=("DEEPSEEK_API_KEY",),
                    environ=env,
                )
            self.assertEqual(env, {"KEEP": "yes"})

    def test_loader_never_reads_real_process_environment_in_injected_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            env = {"DEEPSEEK_API_KEY": "injected"}
            names = load_deepseek_environment(repo_root=root, environ=env)
            self.assertEqual(names, ("DEEPSEEK_API_KEY",))

    def test_formal_runner_loads_credentials_before_batch_creation(self) -> None:
        batch_id = "env-loader-formal-test"
        authorization = authorize_product_live_run(batch_id=batch_id)
        approval = ProductLiveFormalApproval(
            batch_id=batch_id,
            profile_id=PRODUCT_PROFILE_ID,
            inputs_sha256=PRODUCT_INPUTS_SHA256,
            evaluator_labels_sha256=PRODUCT_LABELS_SHA256,
            provider=PRODUCT_PROVIDER,
            model=PRODUCT_MODEL,
            condition=PRODUCT_CONDITION,
            max_batch_http=PRODUCT_MAX_BATCH_HTTP,
            enable_cad_pipeline=True,
            approver="test-owner",
            approved_at_utc="2026-11-14T00:00:00Z",
            approval_statement=f"I approve product live formal execution of batch {batch_id}",
            is_test_only=False,
        )
        with tempfile.TemporaryDirectory() as tmp:
            batch_root = Path(tmp) / "runs"
            with patch("integration.product_live_runner._CANONICAL_RUN_ROOT", batch_root), \
                 patch(
                     "integration.product_live_runner.run_product_offline_preflight",
                     return_value={"ok": True, "errors": [], "details": {}},
                 ), \
                 patch(
                     "integration.product_live_runner.load_deepseek_environment",
                     side_effect=EnvironmentConfigurationError(
                         "required credential environment variable(s) missing or empty: DEEPSEEK_API_KEY"
                     ),
                 ) as load_env:
                with self.assertRaises(ProductLiveConfigurationError):
                    run_product_batch(
                        authorization=authorization,
                        dry_run=False,
                        transport=None,
                        approval=approval,
                    )
                load_env.assert_called_once()
            self.assertFalse(batch_root.exists())

    def test_dry_run_does_not_load_credentials(self) -> None:
        authorization = authorize_product_live_run(batch_id="env-loader-dry-run-test")
        with patch("integration.product_live_runner.load_deepseek_environment") as load_env:
            result = run_product_batch(authorization=authorization, dry_run=True)
        self.assertTrue(result.preflight_ok)
        load_env.assert_not_called()


if __name__ == "__main__":
    unittest.main()

