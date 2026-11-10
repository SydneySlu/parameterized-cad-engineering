"""R3 regression tests for APP-001-ADAPTER corrections.

Covers the two issues confirmed in APP-001-ADAPTER-R2-codex-review.md:

A. Prompt verification bypass removed:
   - Adapter.run() has no verify_frozen_prompt or _prompt_loader_path parameter.
   - Synthetic prompts are rejected unconditionally (send_calls == 0).
   - Tampered artifact (version string preserved, content changed) is rejected
     via file-level SHA-256 anchor.
   - Integration: real frozen prompt + FakeTransport reaches send() successfully.

B. Retention _test_only bypass removed:
   - RetentionPolicy has no _test_only field.
   - RetentionPolicy has no for_test() factory.
   - Direct construction of RetentionPolicy(retain_raw=True, base_dir=<external>)
     is rejected by _resolve_canonical_path before any write.
   - No public policy field can enable writing outside work/app001-runs/.
"""

import hashlib
import inspect
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from src.llm.adapter import (
    Adapter,
    AdapterInput,
    RetentionPolicy,
    _resolve_canonical_path,
    _write_raw_to_dir,
    _retain_response,
)
from src.llm.contract import DEEPSEEK_PROVIDER
from src.llm.prompt_loader import (
    FROZEN_PROMPT_FILE_SHA256,
    FROZEN_PROMPT_PATH,
    FROZEN_PROMPT_VERSION,
    FrozenPromptMismatchError,
    clear_cache,
    load_frozen_prompt,
    verify_adapter_input,
)
from src.llm.transport import FakeTransport, TransportResponse
from tests.llm._frozen_helpers import _frozen_input


def _body():
    return json.dumps({
        "contract_version": "app001-io.v1",
        "prompt_version": "app001-extraction.v5",
        "decision": "answer",
        "extracted_parameters": {"bore_d": 20},
        "unsupported_requests": [],
        "evidence": [{"field": "bore_d", "quote": "20", "source": "user_input"}],
        "missing_fields": [],
        "questions": [],
        "confidence": None,
    })


def _deepseek_response():
    return TransportResponse(
        status=200, body=_body(), runtime_returned_model="deepseek-flash",
        runtime_returned_provider=None,
        usage={"prompt_tokens": 40, "completion_tokens": 6, "total_tokens": 46,
               "prompt_cache_hit_tokens": 0, "prompt_cache_miss_tokens": 40},
    )


class _NoSleep:
    def __call__(self, s):
        raise AssertionError(f"unexpected sleep({s})")


# ---------------------------------------------------------------------------
# A: Prompt verification bypass removed
# ---------------------------------------------------------------------------


class PromptVerificationBypassRemovedTests(unittest.TestCase):
    """R3-A: Adapter.run() must not have bypass parameters."""

    def setUp(self):
        clear_cache()

    def tearDown(self):
        clear_cache()

    def test_run_has_no_verify_frozen_prompt_param(self):
        """R3-A: Adapter.run() signature must not include verify_frozen_prompt."""
        sig = inspect.signature(Adapter.run)
        self.assertNotIn("verify_frozen_prompt", sig.parameters)

    def test_run_has_no_prompt_loader_path_param(self):
        """R3-A: Adapter.run() signature must not include _prompt_loader_path."""
        sig = inspect.signature(Adapter.run)
        self.assertNotIn("_prompt_loader_path", sig.parameters)

    def test_synthetic_prompt_rejected_before_send(self):
        """R3-A: A synthetic (non-frozen) prompt must be rejected; send_calls==0."""
        transport = FakeTransport()
        transport.queue_response(_deepseek_response())
        adapter = Adapter(provider=DEEPSEEK_PROVIDER, transport=transport, sleeper=_NoSleep())
        ai = AdapterInput(
            query_id="q1", natural_language_input="bore_d=20", reference_context=None,
            system_prompt="synthetic not frozen prompt",
            user_prompt_template="query_id: {query_id}\nnatural: {natural_language_input}\nref: {reference_context_or_null}",
            condition_id="c0",
        )
        with self.assertRaises(FrozenPromptMismatchError):
            adapter.run(ai, run_id="r3a1")
        self.assertEqual(transport.call_count, 0)

    def test_frozen_prompt_integration_reaches_send(self):
        """R3-A: Real frozen prompt + FakeTransport must reach send() successfully."""
        transport = FakeTransport()
        transport.queue_response(_deepseek_response())
        adapter = Adapter(provider=DEEPSEEK_PROVIDER, transport=transport, sleeper=_NoSleep())
        ai = _frozen_input(natural_language_input="bore_d=20 mm")
        result = adapter.run(ai, run_id="r3a2")
        self.assertTrue(result.record.construction_ready)
        self.assertEqual(transport.call_count, 1)

    def test_tampered_artifact_rejected_by_file_hash(self):
        """R3-A: A tampered file (version string preserved, content changed)
        must be rejected by the file-level SHA-256 anchor.

        We create a temporary file with the original content, then a second
        file with tampered content (version string preserved).  We call
        ``_verify_file_hash`` on the tampered file using the original file's
        hash as the expected value, proving that any content change is caught
        even when the version marker is intact.
        """
        from src.llm.prompt_loader import _verify_file_hash

        original_bytes = FROZEN_PROMPT_PATH.read_bytes()
        original_hash = hashlib.sha256(original_bytes).hexdigest()
        # Sanity: the anchor matches the current file.
        self.assertEqual(original_hash, FROZEN_PROMPT_FILE_SHA256)

        # Create a tampered copy that preserves the version string.
        original_text = original_bytes.decode("utf-8")
        tampered_text = original_text.replace("APP-001", "APP-001-TAMPERED", 1)
        self.assertNotEqual(original_text, tampered_text)
        self.assertIn(FROZEN_PROMPT_VERSION, tampered_text)  # version string preserved

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False, encoding="utf-8"
        ) as f:
            f.write(tampered_text)
            tampered_path = Path(f.name)
        try:
            # The tampered file's hash must differ from the original.
            tampered_hash = hashlib.sha256(tampered_path.read_bytes()).hexdigest()
            self.assertNotEqual(tampered_hash, original_hash)
            # _verify_file_hash must reject the tampered file.
            with self.assertRaises(FrozenPromptMismatchError) as ctx:
                _verify_file_hash(tampered_path, original_hash)
            self.assertIn("hash mismatch", str(ctx.exception))
        finally:
            tampered_path.unlink(missing_ok=True)

    def test_tampered_file_hash_differs_from_anchor(self):
        """R3-A: A file with changed content must have a different SHA-256
        than the frozen anchor, confirming the anchor catches tampering."""
        original_text = FROZEN_PROMPT_PATH.read_text(encoding="utf-8")
        tampered_text = original_text.replace("set_screw", "set_screw_TAMPERED", 1)
        self.assertNotEqual(original_text, tampered_text)
        self.assertIn(FROZEN_PROMPT_VERSION, tampered_text)
        tampered_hash = hashlib.sha256(tampered_text.encode("utf-8")).hexdigest()
        self.assertNotEqual(tampered_hash, FROZEN_PROMPT_FILE_SHA256)

    def test_file_hash_anchor_is_documented_constant(self):
        """R3-A: FROZEN_PROMPT_FILE_SHA256 must be a 64-char hex string."""
        self.assertEqual(len(FROZEN_PROMPT_FILE_SHA256), 64)
        self.assertRegex(FROZEN_PROMPT_FILE_SHA256, r"^[0-9a-f]{64}$")

    def test_modified_system_prompt_rejected_send_calls_zero(self):
        """R3-A: Modified system prompt → FrozenPromptMismatchError, send_calls==0."""
        artifact = load_frozen_prompt()
        transport = FakeTransport()
        transport.queue_response(_deepseek_response())
        adapter = Adapter(provider=DEEPSEEK_PROVIDER, transport=transport, sleeper=_NoSleep())
        ai = AdapterInput(
            query_id="q1", natural_language_input="bore_d=20", reference_context=None,
            system_prompt=artifact.system_prompt + " extra",
            user_prompt_template=artifact.user_template,
            condition_id="c0",
        )
        with self.assertRaises(FrozenPromptMismatchError):
            adapter.run(ai, run_id="r3a3")
        self.assertEqual(transport.call_count, 0)

    def test_modified_user_template_rejected_send_calls_zero(self):
        """R3-A: Modified user template → FrozenPromptMismatchError, send_calls==0."""
        artifact = load_frozen_prompt()
        transport = FakeTransport()
        transport.queue_response(_deepseek_response())
        adapter = Adapter(provider=DEEPSEEK_PROVIDER, transport=transport, sleeper=_NoSleep())
        ai = AdapterInput(
            query_id="q1", natural_language_input="bore_d=20", reference_context=None,
            system_prompt=artifact.system_prompt,
            user_prompt_template=artifact.user_template + "\nextra",
            condition_id="c0",
        )
        with self.assertRaises(FrozenPromptMismatchError):
            adapter.run(ai, run_id="r3a4")
        self.assertEqual(transport.call_count, 0)

    def test_prompt_text_not_in_exception(self):
        """R3-A: FrozenPromptMismatchError must not contain prompt text."""
        transport = FakeTransport()
        transport.queue_response(_deepseek_response())
        adapter = Adapter(provider=DEEPSEEK_PROVIDER, transport=transport, sleeper=_NoSleep())
        ai = AdapterInput(
            query_id="q1", natural_language_input="bore_d=20", reference_context=None,
            system_prompt="unique_secret_prompt_text_12345",
            user_prompt_template="query_id: {query_id}\nnatural: {natural_language_input}\nref: {reference_context_or_null}",
            condition_id="c0",
        )
        try:
            adapter.run(ai, run_id="r3a5")
            self.fail("should have raised")
        except FrozenPromptMismatchError as exc:
            self.assertNotIn("unique_secret_prompt_text_12345", str(exc))


# ---------------------------------------------------------------------------
# B: Retention _test_only bypass removed
# ---------------------------------------------------------------------------


class RetentionBypassRemovedTests(unittest.TestCase):
    """R3-B: No public field can enable writing outside work/app001-runs/."""

    def test_retention_policy_has_no_test_only_field(self):
        """R3-B: RetentionPolicy dataclass must not have _test_only."""
        import dataclasses
        fields = {f.name for f in dataclasses.fields(RetentionPolicy)}
        self.assertNotIn("_test_only", fields)

    def test_retention_policy_has_no_for_test_factory(self):
        """R3-B: RetentionPolicy must not have for_test classmethod."""
        self.assertFalse(hasattr(RetentionPolicy, "for_test"))

    def test_retention_policy_has_no_validate_for_production(self):
        """R3-B: validate_for_production removed (path check is internal)."""
        self.assertFalse(hasattr(RetentionPolicy, "validate_for_production"))

    def test_external_path_rejected_by_resolver(self):
        """R3-B: External absolute path rejected before any write."""
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError) as ctx:
                _resolve_canonical_path(tmp)
            self.assertIn("RETENTION_PATH_OUTSIDE_IGNORED_DIR", str(ctx.exception))

    def test_path_traversal_rejected(self):
        """R3-B: Path traversal via .. rejected."""
        with self.assertRaises(ValueError) as ctx:
            _resolve_canonical_path("work/app001-runs/../../etc")
        self.assertIn("RETENTION_PATH_OUTSIDE_IGNORED_DIR", str(ctx.exception))

    def test_direct_construction_with_external_base_dir_rejected_on_use(self):
        """R3-B: RetentionPolicy(retain_raw=True, base_dir=<external>) rejected on write."""
        with tempfile.TemporaryDirectory() as tmp:
            policy = RetentionPolicy(retain_raw=True, base_dir=tmp)
            meta = _retain_response("body", "r1", "q1", policy)
            self.assertFalse(meta.get("retained", True))
            self.assertTrue(meta.get("retention_failed"))
            self.assertEqual(meta.get("error"), "RETENTION_PATH_OUTSIDE_IGNORED_DIR")

    def test_write_raw_to_dir_writes_to_tempdir(self):
        """R3-B: Private _write_raw_to_dir can write to a test tempdir."""
        with tempfile.TemporaryDirectory() as tmp:
            meta = _write_raw_to_dir(Path(tmp), "raw body", "run1", "q1")
            self.assertTrue(meta.get("retained"))
            self.assertTrue(os.path.exists(meta["path"]))
            self.assertTrue(meta["path"].startswith(tmp))

    def test_write_failure_recorded(self):
        """R3-B: Write failure must be recorded, not silently swallowed."""
        meta = _write_raw_to_dir(Path("/dev/null/impossible_path_xyz"), "raw", "r", "q")
        self.assertFalse(meta.get("retained", True))
        self.assertTrue(meta.get("retention_failed"))

    def test_default_policy_no_file_written(self):
        """R3-B: Default policy (retain_raw=False) writes no file."""
        transport = FakeTransport()
        transport.queue_response(_deepseek_response())
        adapter = Adapter(provider=DEEPSEEK_PROVIDER, transport=transport, sleeper=_NoSleep())
        result = adapter.run(_frozen_input(), run_id="r3b1")
        meta = result.record.raw_response_retention
        self.assertFalse(meta.get("retained", True))

    def test_no_response_file_outside_canonical_root(self):
        """R3-B: No raw response file should appear outside work/app001-runs/."""
        with tempfile.TemporaryDirectory() as tmp:
            # Try to construct a policy that writes to tmp; it must be rejected.
            policy = RetentionPolicy(retain_raw=True, base_dir=tmp)
            meta = _retain_response("body", "r1", "q1", policy)
            self.assertFalse(meta.get("retained", True))
            # No file should exist in tmp.
            self.assertEqual(os.listdir(tmp), [])

    def test_symlink_escape_rejected(self):
        """R3-FIX: A symlink inside work/app001-runs/ pointing to an external
        directory must be rejected by _resolve_canonical_path.

        No raw response file should appear in the external directory.
        If the platform does not support symlinks, skip with an explicit reason.
        """
        external_dir = tempfile.mkdtemp(prefix="r3_symlink_external_")
        # Create a symlink inside work/app001-runs/ pointing to external_dir.
        canonical_root = _resolve_canonical_path("work/app001-runs")
        canonical_root.mkdir(parents=True, exist_ok=True)
        # Use a unique link name to avoid collisions with prior runs that left
        # undeletable symlinks on FUSE filesystems.
        import time as _time
        link_name = canonical_root / f"escape_link_{int(_time.time() * 1000) % 9999999}"
        try:
            os.symlink(external_dir, link_name)
        except (OSError, NotImplementedError):
            # Platform does not support symlinks, or link already exists.
            shutil.rmtree(external_dir, ignore_errors=True)
            try:
                link_name.unlink(missing_ok=True)
            except OSError:
                pass  # FUSE: cannot delete symlinks; skip
            self.skipTest("symlinks not supported or link creation failed on this platform")
            return
        try:
            # _resolve_canonical_path on the symlink must reject it because
            # .resolve() follows the link to the external directory.
            with self.assertRaises(ValueError) as ctx:
                _resolve_canonical_path(link_name)
            self.assertIn("RETENTION_PATH_OUTSIDE_IGNORED_DIR", str(ctx.exception))
            # No raw response file should exist in the external directory.
            self.assertEqual(os.listdir(external_dir), [])
        finally:
            if link_name.is_symlink() or link_name.exists():
                try:
                    link_name.unlink(missing_ok=True)
                except OSError:
                    pass  # FUSE: cannot delete symlinks; silently ignore
            shutil.rmtree(external_dir, ignore_errors=True)

    def test_symlink_escape_rejected_by_retain_response(self):
        """R3-FIX: _retain_response must not write through a symlink that
        escapes the canonical root."""
        external_dir = tempfile.mkdtemp(prefix="r3_symlink_retain_")
        canonical_root = _resolve_canonical_path("work/app001-runs")
        canonical_root.mkdir(parents=True, exist_ok=True)
        # Use a unique link name to avoid collisions with prior runs that left
        # undeletable symlinks on FUSE filesystems.
        import time as _time
        link_name = canonical_root / f"retain_escape_link_{int(_time.time() * 1000) % 9999999}"
        try:
            os.symlink(external_dir, link_name)
        except (OSError, NotImplementedError):
            import shutil
            shutil.rmtree(external_dir, ignore_errors=True)
            try:
                link_name.unlink(missing_ok=True)
            except OSError:
                pass  # FUSE: cannot delete symlinks; skip
            self.skipTest("symlinks not supported or link creation failed on this platform")
            return
        try:
            # Policy pointing through the symlink must be rejected.
            policy = RetentionPolicy(retain_raw=True, base_dir=str(link_name))
            meta = _retain_response("raw body", "run1", "q1", policy)
            self.assertFalse(meta.get("retained", True))
            self.assertTrue(meta.get("retention_failed"))
            self.assertEqual(meta.get("error"), "RETENTION_PATH_OUTSIDE_IGNORED_DIR")
            # No file should appear in the external directory.
            self.assertEqual(os.listdir(external_dir), [])
        finally:
            if link_name.is_symlink() or link_name.exists():
                try:
                    link_name.unlink(missing_ok=True)
                except OSError:
                    pass  # FUSE: cannot delete symlinks; silently ignore
            import shutil
            shutil.rmtree(external_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
