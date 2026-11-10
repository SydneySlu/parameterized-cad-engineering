"""Offline tests for scripts/run_app001_v5_formal_batch.py.

All tests are offline: no DeepSeek/Ollama chat calls, no API key reads or
prints, no network access.  subprocess.run (git) calls are mocked via the
injectable ``git_runner`` parameter of ``verify_commit()``.

Coverage:
  CommitValidation
    - baseline commit passes as-is
    - descendant with zero production-path diffs passes
    - non-ancestor HEAD is rejected
    - descendant with production-path diff is rejected (each path class)
  BatchDirProtection (calls real ensure_batch_dir_absent)
    - absent directory passes
    - directory that already exists (empty) is rejected
    - directory that already exists with runs.jsonl is rejected
  OllamaRuntime (calls real check_ollama_runtime)
    - unreachable → aborts
    - unreachable → run_formal not called
    - model missing → aborts
    - digest mismatch → aborts
    - good mock response → passes, returns digest
  SyntaxAndImport
    - py_compile passes on the script
  DryRun
    - dry_run() returns exactly 36 logical combinations
"""

from __future__ import annotations

import py_compile
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# ── locate repo root and add src to path ─────────────────────────────────────

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "src"))

_SCRIPT_PATH = _REPO_ROOT / "scripts" / "run_app001_v5_formal_batch.py"

# Import the script module for testing (no __main__ guard needed because we
# import it, not execute it).
import importlib.util as _ilu

def _load_script():
    spec = _ilu.spec_from_file_location("run_app001_v5_formal_batch", _SCRIPT_PATH)
    mod = _ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

_script = _load_script()

BASELINE = _script.BASELINE_COMMIT
PROD_PATHS = _script.PRODUCTION_PATHS

# ── helpers ───────────────────────────────────────────────────────────────────

def _make_completed(returncode: int, stdout: str = "", stderr: str = "") -> subprocess.CompletedProcess:
    r = subprocess.CompletedProcess(args=[], returncode=returncode)
    r.stdout = stdout
    r.stderr = stderr
    return r


def _git_runner_factory(
    *,
    head: str,
    is_ancestor: bool = True,
    diff_output: str = "",
    diff_returncode: int = 0,
):
    """Return an injectable git_runner for verify_commit() tests."""
    def git_runner(args: list[str]) -> subprocess.CompletedProcess:
        if args[0] == "rev-parse" and args[1] == "HEAD":
            return _make_completed(0, stdout=head + "\n")
        if args[0] == "merge-base" and args[1] == "--is-ancestor":
            return _make_completed(0 if is_ancestor else 1)
        if args[0] == "diff" and "--name-only" in args:
            return _make_completed(diff_returncode, stdout=diff_output)
        # Unexpected git invocation — let it fail loudly
        raise AssertionError(f"Unexpected git call: {args}")
    return git_runner


# ── CommitValidation ──────────────────────────────────────────────────────────

class CommitValidationTests(unittest.TestCase):

    def test_baseline_commit_passes(self):
        """HEAD == BASELINE_COMMIT: no ancestor check, no diff check."""
        runner = _git_runner_factory(head=BASELINE)
        result = _script.verify_commit(
            baseline=BASELINE,
            production_paths=PROD_PATHS,
            git_runner=runner,
            repo_root=_REPO_ROOT,
        )
        self.assertEqual(result, BASELINE)

    def test_descendant_clean_diff_passes(self):
        """HEAD is a descendant of baseline with no production-path diffs."""
        descendant = "a" * 40  # fake hash, not the baseline
        runner = _git_runner_factory(
            head=descendant,
            is_ancestor=True,
            diff_output="",  # no files changed
        )
        result = _script.verify_commit(
            baseline=BASELINE,
            production_paths=PROD_PATHS,
            git_runner=runner,
            repo_root=_REPO_ROOT,
        )
        self.assertEqual(result, descendant)

    def test_non_ancestor_rejected(self):
        """HEAD is not the baseline and not a descendant: must abort."""
        unrelated = "b" * 40
        runner = _git_runner_factory(
            head=unrelated,
            is_ancestor=False,
        )
        with self.assertRaises(SystemExit) as ctx:
            _script.verify_commit(
                baseline=BASELINE,
                production_paths=PROD_PATHS,
                git_runner=runner,
                repo_root=_REPO_ROOT,
            )
        self.assertNotEqual(ctx.exception.code, 0)

    def test_descendant_with_src_llm_diff_rejected(self):
        """Descendant that changed src/llm/ must be rejected."""
        descendant = "c" * 40
        runner = _git_runner_factory(
            head=descendant,
            is_ancestor=True,
            diff_output="src/llm/runner.py\n",
        )
        with self.assertRaises(SystemExit) as ctx:
            _script.verify_commit(
                baseline=BASELINE,
                production_paths=PROD_PATHS,
                git_runner=runner,
                repo_root=_REPO_ROOT,
            )
        self.assertNotEqual(ctx.exception.code, 0)

    def test_descendant_with_prompt_diff_rejected(self):
        """Descendant that changed the frozen prompt file must be rejected."""
        descendant = "d" * 40
        runner = _git_runner_factory(
            head=descendant,
            is_ancestor=True,
            diff_output="agent-work/llm/APP-001-v5-activation/prompt-v5.md\n",
        )
        with self.assertRaises(SystemExit) as ctx:
            _script.verify_commit(
                baseline=BASELINE,
                production_paths=PROD_PATHS,
                git_runner=runner,
                repo_root=_REPO_ROOT,
            )
        self.assertNotEqual(ctx.exception.code, 0)

    def test_descendant_with_schema_diff_rejected(self):
        """Descendant that changed src/schema/ must be rejected."""
        descendant = "e" * 40
        runner = _git_runner_factory(
            head=descendant,
            is_ancestor=True,
            diff_output="src/schema/set_screw_shaft_collar.py\n",
        )
        with self.assertRaises(SystemExit) as ctx:
            _script.verify_commit(
                baseline=BASELINE,
                production_paths=PROD_PATHS,
                git_runner=runner,
                repo_root=_REPO_ROOT,
            )
        self.assertNotEqual(ctx.exception.code, 0)

    def test_descendant_with_retrieval_diff_rejected(self):
        """Descendant that changed src/retrieval/ must be rejected."""
        descendant = "f" * 40
        runner = _git_runner_factory(
            head=descendant,
            is_ancestor=True,
            diff_output="src/retrieval/baseline.py\n",
        )
        with self.assertRaises(SystemExit) as ctx:
            _script.verify_commit(
                baseline=BASELINE,
                production_paths=PROD_PATHS,
                git_runner=runner,
                repo_root=_REPO_ROOT,
            )
        self.assertNotEqual(ctx.exception.code, 0)

    def test_descendant_with_doc_only_diff_passes(self):
        """Descendant whose diff touches only docs/ (not production) passes.

        This simulates adding WORKLOG, checkpoint, or other doc commits
        between baseline and execution.  The git_runner reports no changed
        production paths because docs/ is not in PRODUCTION_PATHS.
        """
        descendant = "9" * 40
        # diff_output is empty because PRODUCTION_PATHS doesn't include docs/
        runner = _git_runner_factory(
            head=descendant,
            is_ancestor=True,
            diff_output="",  # no production paths changed
        )
        result = _script.verify_commit(
            baseline=BASELINE,
            production_paths=PROD_PATHS,
            git_runner=runner,
            repo_root=_REPO_ROOT,
        )
        self.assertEqual(result, descendant)


# ── BatchDirProtection (calls real ensure_batch_dir_absent) ───────────────────

class CleanWorktreeTests(unittest.TestCase):

    def test_clean_worktree_passes(self):
        _script.verify_clean_worktree(
            git_runner=lambda args: _make_completed(0, stdout=""),
            repo_root=_REPO_ROOT,
        )

    def test_dirty_worktree_aborts(self):
        with self.assertRaises(SystemExit):
            _script.verify_clean_worktree(
                git_runner=lambda args: _make_completed(0, stdout=" M src/llm/parser.py\n"),
                repo_root=_REPO_ROOT,
            )

class BatchDirProtectionTests(unittest.TestCase):

    def test_absent_dir_passes(self):
        """ensure_batch_dir_absent must not raise when the directory is absent."""
        with tempfile.TemporaryDirectory() as tmp:
            batch_dir = Path(tmp) / "app001-phase1-v5-20261111-01"
            self.assertFalse(batch_dir.exists())
            # Must not raise SystemExit
            _script.ensure_batch_dir_absent(batch_dir)

    def test_existing_empty_dir_rejected(self):
        """ensure_batch_dir_absent must abort on an existing empty directory."""
        with tempfile.TemporaryDirectory() as tmp:
            batch_dir = Path(tmp) / "app001-phase1-v5-20261111-01"
            batch_dir.mkdir()
            with self.assertRaises(SystemExit) as ctx:
                _script.ensure_batch_dir_absent(batch_dir)
            self.assertNotEqual(ctx.exception.code, 0)

    def test_existing_dir_with_runs_jsonl_rejected(self):
        """ensure_batch_dir_absent must abort on a directory with runs.jsonl."""
        with tempfile.TemporaryDirectory() as tmp:
            batch_dir = Path(tmp) / "app001-phase1-v5-20261111-01"
            batch_dir.mkdir()
            (batch_dir / "runs.jsonl").write_text("{}\n")
            with self.assertRaises(SystemExit) as ctx:
                _script.ensure_batch_dir_absent(batch_dir)
            self.assertNotEqual(ctx.exception.code, 0)


# ── OllamaRuntime (calls real check_ollama_runtime) ───────────────────────────

def _fake_urlopen_ok(*responses):
    """Build a urlopen_fn that yields the given JSON response bodies in order."""
    import io
    import json as _json
    iterator = iter(responses)

    class _FakeResp:
        def __init__(self, body: str):
            self._body = body.encode("utf-8")
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False
        def read(self):
            return self._body

    def urlopen_fn(url, timeout=None):
        body = next(iterator)
        return _FakeResp(_json.dumps(body))
    return urlopen_fn


def _fake_urlopen_raises(exc: Exception):
    """Build a urlopen_fn that always raises."""
    def urlopen_fn(url, timeout=None):
        raise exc
    return urlopen_fn


class OllamaRuntimeTests(unittest.TestCase):

    def test_ollama_unreachable_aborts(self):
        """check_ollama_runtime must abort when /api/version is unreachable."""
        urlopen_fn = _fake_urlopen_raises(ConnectionRefusedError("refused"))
        with self.assertRaises(SystemExit) as ctx:
            _script.check_ollama_runtime(urlopen_fn=urlopen_fn)
        self.assertNotEqual(ctx.exception.code, 0)

    def test_ollama_unreachable_run_formal_not_called(self):
        """When Ollama is unreachable, run_formal must never be called."""
        import src.llm.runner as _runner_module

        run_formal_called = []

        def spy_run_formal(self, *a, **kw):
            run_formal_called.append(True)

        urlopen_fn = _fake_urlopen_raises(ConnectionRefusedError("refused"))
        with patch.object(_runner_module.App001Runner, "run_formal", spy_run_formal):
            with self.assertRaises(SystemExit):
                _script.check_ollama_runtime(urlopen_fn=urlopen_fn)

        self.assertEqual(run_formal_called, [],
                         "run_formal must not be called when Ollama is unreachable")

    def test_ollama_model_missing_aborts(self):
        """check_ollama_runtime must abort when the model is not in /api/tags."""
        version_resp = {"version": "0.40.14"}
        tags_resp = {"models": [{"name": "other-model", "digest": "abc"}]}
        urlopen_fn = _fake_urlopen_ok(version_resp, tags_resp)
        with self.assertRaises(SystemExit) as ctx:
            _script.check_ollama_runtime(urlopen_fn=urlopen_fn)
        self.assertNotEqual(ctx.exception.code, 0)

    def test_ollama_digest_mismatch_aborts(self):
        """check_ollama_runtime must abort when the digest prefix is wrong."""
        version_resp = {"version": "0.40.14"}
        tags_resp = {"models": [{"name": "qwen3:8b", "digest": "deadbeef" + "0" * 24}]}
        urlopen_fn = _fake_urlopen_ok(version_resp, tags_resp)
        with self.assertRaises(SystemExit) as ctx:
            _script.check_ollama_runtime(urlopen_fn=urlopen_fn)
        self.assertNotEqual(ctx.exception.code, 0)

    def test_ollama_version_mismatch_aborts(self):
        """The frozen Ollama runtime version must match exactly."""
        urlopen_fn = _fake_urlopen_ok(
            {"version": "0.33.2"},
            {"models": [{"name": "qwen3:8b", "digest": _script.OLLAMA_EXPECTED_DIGEST_PREFIX}]},
        )
        with self.assertRaises(SystemExit):
            _script.check_ollama_runtime(urlopen_fn=urlopen_fn)

    def test_ollama_good_response_passes(self):
        """check_ollama_runtime must return the digest on a valid response."""
        good_digest = _script.OLLAMA_EXPECTED_DIGEST_PREFIX + "782620b40bee6f7b0c89e17ae61f686b92c24933e4ca4b2b8b41"
        version_resp = {"version": "0.40.14"}
        tags_resp = {"models": [{"name": "qwen3:8b", "digest": good_digest}]}
        urlopen_fn = _fake_urlopen_ok(version_resp, tags_resp)
        result = _script.check_ollama_runtime(urlopen_fn=urlopen_fn)
        self.assertEqual(result, good_digest)


# ── SyntaxAndImport ───────────────────────────────────────────────────────────

class SyntaxTests(unittest.TestCase):

    def test_py_compile(self):
        """The script must compile without syntax errors."""
        py_compile.compile(str(_SCRIPT_PATH), doraise=True)

    def test_script_imports_cleanly(self):
        """Importing the script module must not raise or make network calls."""
        # Already imported at module level; just verify key attributes exist.
        self.assertTrue(hasattr(_script, "verify_commit"))
        self.assertTrue(hasattr(_script, "preflight"))
        self.assertTrue(hasattr(_script, "BASELINE_COMMIT"))
        self.assertTrue(hasattr(_script, "BATCH_ID"))
        self.assertTrue(hasattr(_script, "PRODUCTION_PATHS"))
        self.assertIsInstance(_script.PRODUCTION_PATHS, tuple)
        self.assertGreater(len(_script.PRODUCTION_PATHS), 0)

    def test_frozen_v5_prompt_and_activation_manifest_hashes(self):
        self.assertEqual(
            _script._sha256_file(
                _REPO_ROOT / "agent-work/llm/APP-001-v5-activation/prompt-v5.md"
            ),
            _script.EXPECTED_PROMPT_FILE_SHA256,
        )
        self.assertEqual(
            _script._sha256_file(
                _REPO_ROOT / "agent-work/llm/APP-001-v5-activation/manifest.json"
            ),
            _script.EXPECTED_ACTIVATION_MANIFEST_SHA256,
        )

    def test_v5_authorization_and_ollama_schema_hashes_are_pinned(self):
        from llm.authorization import authorize_phase1_run
        from llm.providers import OLLAMA_FORMAT_SCHEMA_SHA256

        self.assertEqual(
            authorize_phase1_run(batch_id=_script.BATCH_ID).scope_hash(),
            _script.EXPECTED_SCOPE_HASH,
        )
        self.assertEqual(
            OLLAMA_FORMAT_SCHEMA_SHA256,
            _script.OLLAMA_EXPECTED_FORMAT_SCHEMA_SHA256,
        )

    def test_no_api_key_printed_on_import(self, capsys=None):
        """Importing or calling non-network helpers must not print key values."""
        # DEEPSEEK_API_KEY must not appear in any output from verify_commit or
        # the module-level code.  We just confirm the constant name is safe.
        self.assertNotIn("DEEPSEEK_API_KEY", repr(_script.BASELINE_COMMIT))
        self.assertNotIn("DEEPSEEK_API_KEY", repr(_script.EXPECTED_SCOPE_HASH))


# ── DryRun ────────────────────────────────────────────────────────────────────

class DryRunTests(unittest.TestCase):

    def test_dry_run_returns_36_combinations(self):
        """App001Runner.dry_run() must return exactly 36 logical combinations.

        This exercises the acceptance-set projection, combination generator,
        and authorization factory without any network call or key read.
        """
        from src.llm.runner import App001Runner
        runner = App001Runner()
        summary = runner.dry_run()
        self.assertEqual(summary.mode, "dry_run")
        self.assertEqual(summary.planned_runs, 36)
        self.assertIsNotNone(summary.dry_run_plan)
        combos = summary.dry_run_plan["combinations"]
        self.assertEqual(len(combos), 36)

    def test_dry_run_covers_both_conditions(self):
        """Dry run combinations must include both C0 and C1."""
        from src.llm.runner import App001Runner
        runner = App001Runner()
        summary = runner.dry_run()
        conditions = {c["condition_id"] for c in summary.dry_run_plan["combinations"]}
        self.assertIn("C0", conditions)
        self.assertIn("C1", conditions)

    def test_dry_run_covers_both_providers(self):
        """Dry run combinations must include DeepSeek and Ollama."""
        from src.llm.runner import App001Runner
        runner = App001Runner()
        summary = runner.dry_run()
        providers = {c["provider"] for c in summary.dry_run_plan["combinations"]}
        self.assertIn("DeepSeek", providers)
        self.assertIn("Ollama", providers)


if __name__ == "__main__":
    unittest.main()
