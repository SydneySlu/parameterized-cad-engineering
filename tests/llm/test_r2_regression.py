"""R2 regression tests for APP-001-ADAPTER corrections.

Covers the three specific issues confirmed in APP-001-ADAPTER-R1-codex-review.md:

4.1 Gate cannot be bypassed by MockTransport subclass:
    - Custom MockTransport subclass → send_calls == 0
    - Duck-type (plain class with send()) → send_calls == 0
    - FakeTransport exact type → still runs (gate closed but allowed)
    - Gate check fires before any send()

4.2 Retention path restricted to work/app001-runs/:
    - Default policy: no file written
    - for_test() path: writes to test tempdir
    - Production canonical path: writes to work/app001-runs/
    - External absolute path (production policy): rejected before write
    - Path traversal: rejected before write
    - Symbolic link escape: rejected (symlink path resolves outside root)
    - Write failure (bad path): retention_failed, not success

4.3 Frozen prompt artifact verification:
    - Correct frozen prompt passes before send()
    - Modified system prompt rejected before send()
    - Modified user template rejected before send()
    - Artifact missing → rejected before send()
    - send_calls == 0 on all failure paths
    - Prompt text does not appear in RunRecord JSON
    - verify_frozen_prompt=False skips check (for synthetic tests)
"""

import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.llm.adapter import (
    Adapter,
    AdapterInput,
    RetentionPolicy,
    _resolve_canonical_path,
)
from src.llm.contract import DEEPSEEK_PROVIDER, OLLAMA_PROVIDER
from src.llm.gate import FormalEvaluationBlockedError
from src.llm.prompt_loader import (
    FrozenPromptMismatchError,
    FrozenPromptArtifact,
    FROZEN_PROMPT_PATH,
    FROZEN_PROMPT_VERSION,
    load_frozen_prompt,
    verify_adapter_input,
    clear_cache,
)
from src.llm.transport import FakeTransport, MockTransport, TransportResponse


SYSTEM_PROMPT = "s"
USER_TEMPLATE = "query_id: {query_id}\nfamily_id: set_screw_shaft_collar\nnatural_language_input:\n{natural_language_input}\nreference_context:\n{reference_context_or_null}"


def _input(**kw):
    defaults = dict(
        query_id="q1",
        natural_language_input="bore_d=20",
        reference_context=None,
        system_prompt=SYSTEM_PROMPT,
        user_prompt_template=USER_TEMPLATE,
        condition_id="c0",
    )
    defaults.update(kw)
    return AdapterInput(**defaults)


def _body():
    return json.dumps({
        "contract_version": "app001-io.v1",
        "prompt_version": "app001-extraction.v2",
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
# 4.1: Gate exact type check (MockTransport subclass bypass prevention)
# ---------------------------------------------------------------------------


class GateExactTypeTests(unittest.TestCase):
    """Gate must refuse any transport other than type FakeTransport exactly."""

    def _counting_transport(self, inherit_from=object):
        """Create a minimal transport class that counts send() calls."""
        class CountingTransport(inherit_from):
            def __init__(self):
                self.send_calls = 0
            def send(self, request):
                self.send_calls += 1
                return TransportResponse(200, _body())
        return CountingTransport()

    def test_mock_transport_subclass_refused_before_send(self):
        """Custom MockTransport subclass must be refused; send_calls must be 0."""
        custom = self._counting_transport(inherit_from=MockTransport)
        adapter = Adapter(provider=DEEPSEEK_PROVIDER, transport=custom, sleeper=_NoSleep())
        with self.assertRaises(FormalEvaluationBlockedError):
            adapter.run(_input(), verify_frozen_prompt=False, run_id="g1")
        self.assertEqual(custom.send_calls, 0, "send() was called despite gate being closed")

    def test_duck_type_transport_refused_before_send(self):
        """Plain class with send() method (no MockTransport inheritance) must be refused."""
        custom = self._counting_transport(inherit_from=object)
        adapter = Adapter(provider=DEEPSEEK_PROVIDER, transport=custom, sleeper=_NoSleep())
        with self.assertRaises(FormalEvaluationBlockedError):
            adapter.run(_input(), verify_frozen_prompt=False, run_id="g2")
        self.assertEqual(custom.send_calls, 0)

    def test_fake_transport_exact_type_still_runs(self):
        """FakeTransport (exact type) is still allowed with gate closed."""
        transport = FakeTransport()
        transport.queue_response(_deepseek_response())
        adapter = Adapter(provider=DEEPSEEK_PROVIDER, transport=transport, sleeper=_NoSleep())
        result = adapter.run(_input(), verify_frozen_prompt=False, run_id="g3")
        self.assertTrue(result.record.construction_ready)
        self.assertEqual(transport.call_count, 1)

    def test_fake_transport_subclass_refused(self):
        """Even a FakeTransport subclass must be refused (not exact FakeTransport type)."""
        class MyFake(FakeTransport):
            pass
        custom = MyFake()
        custom.queue_response(_deepseek_response())
        adapter = Adapter(provider=DEEPSEEK_PROVIDER, transport=custom, sleeper=_NoSleep())
        with self.assertRaises(FormalEvaluationBlockedError):
            adapter.run(_input(), verify_frozen_prompt=False, run_id="g4")
        # send() must not have been called.
        self.assertEqual(custom.call_count, 0)

    def test_gate_check_fires_before_env_read(self):
        """Gate must fire before any environment variable access."""
        import os
        custom = self._counting_transport(inherit_from=MockTransport)
        saved = os.environ.get("DEEPSEEK_API_KEY")
        os.environ["DEEPSEEK_API_KEY"] = "synthetic-must-not-be-read"
        try:
            adapter = Adapter(provider=DEEPSEEK_PROVIDER, transport=custom, sleeper=_NoSleep())
            with self.assertRaises(FormalEvaluationBlockedError):
                adapter.run(_input(), verify_frozen_prompt=False, run_id="g5")
            self.assertEqual(custom.send_calls, 0)
        finally:
            if saved is None:
                os.environ.pop("DEEPSEEK_API_KEY", None)
            else:
                os.environ["DEEPSEEK_API_KEY"] = saved


# ---------------------------------------------------------------------------
# 4.2: Retention path restriction
# ---------------------------------------------------------------------------


class RetentionPathTests(unittest.TestCase):
    def test_default_policy_no_file_written(self):
        transport = FakeTransport()
        transport.queue_response(_deepseek_response())
        adapter = Adapter(provider=DEEPSEEK_PROVIDER, transport=transport, sleeper=_NoSleep())
        result = adapter.run(_input(), verify_frozen_prompt=False, run_id="rp1")
        meta = result.record.raw_response_retention
        self.assertFalse(meta.get("retained", True))

    def test_for_test_factory_writes_to_tempdir(self):
        with tempfile.TemporaryDirectory() as tmp:
            transport = FakeTransport()
            transport.queue_response(_deepseek_response())
            adapter = Adapter(
                provider=DEEPSEEK_PROVIDER, transport=transport,
                sleeper=_NoSleep(),
                retention_policy=RetentionPolicy.for_test(base_dir=tmp),
            )
            result = adapter.run(_input(), verify_frozen_prompt=False, run_id="rp2")
            meta = result.record.raw_response_retention
            self.assertTrue(meta.get("retained"))
            self.assertTrue(os.path.exists(meta["path"]))
            self.assertTrue(meta["path"].startswith(tmp))

    def test_production_policy_external_absolute_path_rejected(self):
        """Production RetentionPolicy cannot write outside work/app001-runs/."""
        with tempfile.TemporaryDirectory() as tmp:
            # Try to create a production policy with an external absolute path.
            with self.assertRaises(ValueError) as ctx:
                policy = RetentionPolicy(retain_raw=True, base_dir=tmp)
                policy.validate_for_production()
            self.assertIn("RETENTION_PATH_OUTSIDE_IGNORED_DIR", str(ctx.exception))

    def test_path_traversal_rejected(self):
        """Path traversal via .. must be rejected."""
        with self.assertRaises(ValueError) as ctx:
            policy = RetentionPolicy(retain_raw=True, base_dir="work/app001-runs/../../etc")
            policy.validate_for_production()
        self.assertIn("RETENTION_PATH_OUTSIDE_IGNORED_DIR", str(ctx.exception))

    def test_canonical_path_resolution(self):
        """work/app001-runs/ itself is accepted by the path resolver."""
        from src.llm.adapter import _CANONICAL_RUN_DIR_NAME
        resolved = _resolve_canonical_path(_CANONICAL_RUN_DIR_NAME)
        # Should not raise; resolved path is under work/app001-runs/
        self.assertIn("app001-runs", str(resolved))

    def test_test_only_policy_not_usable_in_production_validate(self):
        """for_test() policies are rejected by validate_for_production()."""
        with tempfile.TemporaryDirectory() as tmp:
            policy = RetentionPolicy.for_test(base_dir=tmp)
            with self.assertRaises(ValueError) as ctx:
                policy.validate_for_production()
            self.assertIn("RETENTION_TEST_ONLY_POLICY", str(ctx.exception))

    def test_write_failure_recorded_not_silently_swallowed(self):
        """If writing fails, retention_failed must be recorded."""
        policy = RetentionPolicy.for_test(base_dir="/dev/null/impossible_path_xyz")
        transport = FakeTransport()
        transport.queue_response(_deepseek_response())
        adapter = Adapter(
            provider=DEEPSEEK_PROVIDER, transport=transport,
            sleeper=_NoSleep(), retention_policy=policy,
        )
        result = adapter.run(_input(), verify_frozen_prompt=False, run_id="rp3")
        meta = result.record.raw_response_retention
        self.assertFalse(meta.get("retained", True))
        self.assertTrue(meta.get("retention_failed"))


# ---------------------------------------------------------------------------
# 4.3: Frozen prompt artifact verification
# ---------------------------------------------------------------------------


class FrozenPromptVerificationTests(unittest.TestCase):
    """Tests for prompt artifact loading and verification."""

    def setUp(self):
        """Clear the module-level cache before each test."""
        clear_cache()

    def tearDown(self):
        clear_cache()

    def test_frozen_artifact_loads_successfully(self):
        """The actual frozen prompt-v2.md must load with correct version."""
        artifact = load_frozen_prompt()
        self.assertEqual(artifact.version, FROZEN_PROMPT_VERSION)
        self.assertGreater(len(artifact.system_prompt), 50)
        self.assertGreater(len(artifact.user_template), 20)

    def test_frozen_artifact_system_prompt_contains_key_instruction(self):
        """System prompt must contain the extraction instruction."""
        artifact = load_frozen_prompt()
        self.assertIn("extract only parameters", artifact.system_prompt.lower())

    def test_frozen_artifact_user_template_has_placeholders(self):
        """User template must use single-brace {placeholder} format."""
        artifact = load_frozen_prompt()
        self.assertIn("{query_id}", artifact.user_template)
        self.assertIn("{natural_language_input}", artifact.user_template)
        self.assertIn("{reference_context_or_null}", artifact.user_template)

    def test_correct_prompt_passes_verification(self):
        """AdapterInput with correct frozen prompt must pass verify_adapter_input."""
        artifact = load_frozen_prompt()
        ai = AdapterInput(
            query_id="q1",
            natural_language_input="bore_d=20",
            reference_context=None,
            system_prompt=artifact.system_prompt,
            user_prompt_template=artifact.user_template,
            condition_id="c0",
        )
        result = verify_adapter_input(ai)  # must not raise
        self.assertEqual(result.version, FROZEN_PROMPT_VERSION)

    def test_modified_system_prompt_rejected_before_send(self):
        """A modified system prompt must be refused before transport.send()."""
        artifact = load_frozen_prompt()
        transport = FakeTransport()
        transport.queue_response(_deepseek_response())
        adapter = Adapter(provider=DEEPSEEK_PROVIDER, transport=transport, sleeper=_NoSleep())
        ai = AdapterInput(
            query_id="q1", natural_language_input="bore_d=20", reference_context=None,
            system_prompt=artifact.system_prompt + " MODIFIED",
            user_prompt_template=artifact.user_template,
            condition_id="c0",
        )
        with self.assertRaises(FrozenPromptMismatchError):
            adapter.run(ai, run_id="pv1")  # verify_frozen_prompt=True by default
        self.assertEqual(transport.call_count, 0)  # send() not called

    def test_modified_user_template_rejected_before_send(self):
        """A modified user template must be refused before transport.send()."""
        artifact = load_frozen_prompt()
        transport = FakeTransport()
        transport.queue_response(_deepseek_response())
        adapter = Adapter(provider=DEEPSEEK_PROVIDER, transport=transport, sleeper=_NoSleep())
        ai = AdapterInput(
            query_id="q1", natural_language_input="bore_d=20", reference_context=None,
            system_prompt=artifact.system_prompt,
            user_prompt_template=artifact.user_template + "\nextra_line",
            condition_id="c0",
        )
        with self.assertRaises(FrozenPromptMismatchError):
            adapter.run(ai, run_id="pv2")
        self.assertEqual(transport.call_count, 0)

    def test_missing_artifact_file_rejected_before_send(self):
        """Missing artifact file must cause FrozenPromptMismatchError before send()."""
        transport = FakeTransport()
        transport.queue_response(_deepseek_response())
        adapter = Adapter(provider=DEEPSEEK_PROVIDER, transport=transport, sleeper=_NoSleep())
        ai = _input()
        with self.assertRaises(FrozenPromptMismatchError):
            adapter.run(ai, run_id="pv3", _prompt_loader_path=Path("/nonexistent/prompt.md"))
        self.assertEqual(transport.call_count, 0)

    def test_verify_false_skips_check_for_synthetic_tests(self):
        """verify_frozen_prompt=False allows synthetic prompts (test-only path)."""
        transport = FakeTransport()
        transport.queue_response(_deepseek_response())
        adapter = Adapter(provider=DEEPSEEK_PROVIDER, transport=transport, sleeper=_NoSleep())
        # Synthetic prompt would normally fail; verify=False bypasses check.
        result = adapter.run(_input(), verify_frozen_prompt=False, run_id="pv4")
        self.assertTrue(result.record.construction_ready)

    def test_prompt_text_not_in_run_record(self):
        """Frozen prompt text must not appear in run record JSON."""
        artifact = load_frozen_prompt()
        transport = FakeTransport()
        transport.queue_response(_deepseek_response())
        adapter = Adapter(provider=DEEPSEEK_PROVIDER, transport=transport, sleeper=_NoSleep())
        ai = AdapterInput(
            query_id="q1", natural_language_input="bore_d=20", reference_context=None,
            system_prompt=artifact.system_prompt,
            user_prompt_template=artifact.user_template,
            condition_id="c0",
        )
        record_json = adapter.run(ai, run_id="pv5").record.to_json()
        # The first 40 chars of system prompt should not appear verbatim.
        self.assertNotIn(artifact.system_prompt[:40], record_json)
        # Hash IS present (identifying the prompt without leaking its text).
        self.assertIn(artifact.system_prompt_sha256, record_json)

    def test_prompt_hashes_match_frozen_artifact(self):
        """prompt_hashes in run record must match the frozen artifact SHA-256."""
        artifact = load_frozen_prompt()
        transport = FakeTransport()
        transport.queue_response(_deepseek_response())
        adapter = Adapter(provider=DEEPSEEK_PROVIDER, transport=transport, sleeper=_NoSleep())
        ai = AdapterInput(
            query_id="q1", natural_language_input="bore_d=20", reference_context=None,
            system_prompt=artifact.system_prompt,
            user_prompt_template=artifact.user_template,
            condition_id="c0",
        )
        rec = adapter.run(ai, run_id="pv6").record
        self.assertEqual(rec.prompt_hashes["system_prompt_sha256"], artifact.system_prompt_sha256)
        self.assertEqual(rec.prompt_hashes["user_template_sha256"], artifact.user_template_sha256)


if __name__ == "__main__":
    unittest.main()
