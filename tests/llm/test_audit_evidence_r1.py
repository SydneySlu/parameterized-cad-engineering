from __future__ import annotations

import hashlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class AuditEvidenceR1Tests(unittest.TestCase):
    def test_successful_wrapper_with_invalid_model_json_is_not_transport_failure(self):
        from llm.real_transport import _parse_with_diagnostic_retention
        from llm.transport import TransportResponse

        retained = []
        content = "not-json"
        response = _parse_with_diagnostic_retention(
            lambda: TransportResponse(status=200, body=content),
            '{"choices":[{"message":{"content":"not-json"}}]}',
            retained.append,
        )
        self.assertEqual(response.body, content)
        self.assertEqual(retained, [])

    def test_adapter_retains_invalid_model_content_with_parse_error(self):
        import json
        import shutil
        import llm.adapter as adapter_module
        from llm.adapter import Adapter, RetentionPolicy
        from llm.contract import DEEPSEEK_MODEL, DEEPSEEK_PROVIDER
        from llm.transport import FakeTransport, TransportResponse
        from tests.llm._frozen_helpers import _frozen_input

        adapter_module._CANONICAL_RUN_DIR.mkdir(parents=True, exist_ok=True)
        batch_dir = Path(tempfile.mkdtemp(prefix="r1-adapter-test-", dir=adapter_module._CANONICAL_RUN_DIR))
        old_root = adapter_module._CANONICAL_RUN_DIR
        adapter_module._CANONICAL_RUN_DIR = batch_dir.parent
        raw = "not a valid model JSON envelope"
        transport = FakeTransport()
        transport.queue_response(TransportResponse(
            status=200, body=raw, runtime_returned_model=DEEPSEEK_MODEL,
            usage={"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2,
                   "prompt_cache_hit_tokens": 0, "prompt_cache_miss_tokens": 1},
        ))
        try:
            policy = RetentionPolicy(retain_raw=True, base_dir=str(batch_dir))
            result = Adapter(provider=DEEPSEEK_PROVIDER, transport=transport,
                             retention_policy=policy).run(_frozen_input(), run_id="diag")
            self.assertEqual(result.record.stage_status("parse"), "fail")
            meta = result.record.raw_response_retention
            self.assertTrue(meta["retained"])
            self.assertFalse(Path(meta["path"]).is_absolute())
            retained = (Path(__file__).resolve().parents[2] / meta["path"]).read_text(encoding="utf-8")
            self.assertEqual(retained, raw)
            self.assertNotIn(raw, json.dumps(result.record.as_dict()))
        finally:
            adapter_module._CANONICAL_RUN_DIR = old_root
            shutil.rmtree(batch_dir, ignore_errors=True)

    def test_invalid_transport_wrapper_retains_raw_and_preserves_error(self):
        from llm.real_transport import _parse_with_diagnostic_retention
        from llm.transport import COND_INVALID_JSON, TransportError

        body = '{"error":"redacted-test-body"}'
        retained = []

        def retainer(value):
            retained.append(value)
            return {"retained": True, "body_sha256": hashlib.sha256(value.encode()).hexdigest()}

        with self.assertRaises(TransportError) as raised:
            _parse_with_diagnostic_retention(
                lambda: (_ for _ in ()).throw(TransportError(COND_INVALID_JSON, 200, "bad wrapper")),
                body,
                retainer,
            )
        self.assertEqual(raised.exception.condition, COND_INVALID_JSON)
        self.assertEqual(raised.exception.message, "bad wrapper")
        self.assertEqual(raised.exception.diagnostic_retention["body_sha256"], hashlib.sha256(body.encode()).hexdigest())
        self.assertEqual(retained, [body])
        self.assertNotIn(body, raised.exception.message)

    def test_retention_failure_does_not_replace_transport_error(self):
        from llm.real_transport import _parse_with_diagnostic_retention
        from llm.transport import COND_INVALID_JSON, TransportError

        with self.assertRaises(TransportError) as raised:
            _parse_with_diagnostic_retention(
                lambda: (_ for _ in ()).throw(TransportError(COND_INVALID_JSON, 200, "wrapper invalid")),
                "private body",
                lambda _body: (_ for _ in ()).throw(OSError("write denied")),
            )
        self.assertEqual(raised.exception.condition, COND_INVALID_JSON)
        self.assertEqual(raised.exception.message, "wrapper invalid")
        self.assertEqual(raised.exception.diagnostic_retention["retained"], False)
        self.assertNotIn("private body", repr(raised.exception))

    def test_5xx_handler_does_not_read_http_error_body(self):
        import urllib.error
        from llm.real_transport import DeepSeekTransport
        from llm.transport import COND_HTTP_5XX, TransportError

        transport = object.__new__(DeepSeekTransport)
        error = urllib.error.HTTPError("https://example.invalid", 503, "unavailable", {}, io.BytesIO(b"must stay unread"))
        error.fp = type("BodyMustNotBeRead", (), {
            "read": lambda self, *args, **kwargs: (_ for _ in ()).throw(AssertionError("HTTPError body must not be read")),
            "close": lambda self: None,
        })()
        with self.assertRaises(TransportError) as raised:
            transport._handle_http_error(error)
        error.close()
        self.assertEqual(raised.exception.condition, COND_HTTP_5XX)

    def test_wrapper_shape_errors_are_classified_and_retained(self):
        import json
        from llm.real_transport import DeepSeekTransport, _parse_with_diagnostic_retention
        from llm.transport import COND_INVALID_JSON, TransportError

        transport = object.__new__(DeepSeekTransport)
        invalid_wrappers = (
            '{"choices":[7]}',
            '{"choices":[{"message":{"content":7}}]}',
            '{"choices":[{"message":{"content":"{}"}}],"usage":[]}',
        )
        for raw in invalid_wrappers:
            with self.subTest(raw=raw):
                retained = []
                with self.assertRaises(TransportError) as raised:
                    _parse_with_diagnostic_retention(
                        lambda: transport._parse_response(200, raw), raw, retained.append
                    )
                self.assertEqual(raised.exception.condition, COND_INVALID_JSON)
                self.assertEqual(retained, [raw])

    def test_retention_metadata_is_bounded_and_hashed(self):
        import llm.adapter as adapter
        import shutil

        adapter._CANONICAL_RUN_DIR.mkdir(parents=True, exist_ok=True)
        td = Path(tempfile.mkdtemp(prefix="r1-test-", dir=adapter._CANONICAL_RUN_DIR))
        try:
            policy = adapter.RetentionPolicy(retain_raw=True, base_dir=str(td))
            body = "x" * (70 * 1024)
            meta = adapter._retain_response(body, "run", "q", policy)
            self.assertTrue(meta["retained"])
            self.assertEqual(meta["body_length"], 70 * 1024)
            self.assertEqual(meta["saved_length"], 64 * 1024)
            self.assertTrue(meta["truncated"])
            self.assertEqual(meta["body_sha256"], hashlib.sha256(body.encode()).hexdigest())
            self.assertFalse(Path(meta["path"]).is_absolute())
        finally:
            shutil.rmtree(td, ignore_errors=True)

    def test_retention_metadata_omits_absolute_path_when_write_fails(self):
        import llm.adapter as adapter

        with tempfile.TemporaryDirectory() as td, patch.object(adapter, "_write_raw_to_dir", return_value={
            "retained": False, "retention_failed": True, "error": "PermissionError"
        }):
            old_root = adapter._CANONICAL_RUN_DIR
            adapter._CANONICAL_RUN_DIR = Path(td)
            try:
                meta = adapter._retain_response("body", "run", "q", adapter.RetentionPolicy(True, td))
            finally:
                adapter._CANONICAL_RUN_DIR = old_root
        self.assertTrue(meta["retention_failed"])
        self.assertNotIn("path", meta)

    def test_blocked_audit_has_no_user_text(self):
        from llm.authorization import authorize_phase1_run
        from llm.combinations import LogicalRunCombination
        from llm.runner import App001Runner

        auth = authorize_phase1_run(batch_id="audit-test")
        combo = LogicalRunCombination(
            logical_run_id="audit-test__q__C1__DeepSeek",
            query_id="q",
            condition_id="C1",
            provider="DeepSeek",
            model="deepseek-flash",
            index=0,
        )
        record = App001Runner()._blocked_audit_record(
            combo, auth, None, None,
            stage_name="c1_query_extraction",
            error_code="C1_NO_SAFE_QUERY_PARAMETER",
            error_fields=("bore_d",),
        )
        self.assertEqual(record["acceptance_set_version"], "acceptance-set-v0")
        self.assertEqual(record["logical_run_id"], combo.logical_run_id)
        self.assertEqual(record["batch_id"], auth.batch_id)
        self.assertIn("configured_provider", record)
        self.assertIn("software_versions", record)
        self.assertEqual(record["prompt_hashes"]["unavailable_reason"], "request_not_constructed")
        self.assertNotIn("natural_language_input", record)
        self.assertNotIn("evaluator", str(record).lower())
        self.assertEqual(record["error_code"], "C1_NO_SAFE_QUERY_PARAMETER")
        self.assertEqual(record["error_fields"], ["bore_d"])

    def test_blocked_audit_has_real_prompt_hashes_when_artifact_available(self):
        from llm.authorization import authorize_phase1_run
        from llm.combinations import LogicalRunCombination
        from llm.prompt_loader import load_frozen_prompt
        from llm.runner import App001Runner

        auth = authorize_phase1_run(batch_id="audit-test-hashes")
        combo = LogicalRunCombination("rid", "q", "C1", "DeepSeek", "deepseek-flash", 0)
        artifact = load_frozen_prompt()
        record = App001Runner()._blocked_audit_record(
            combo, auth, artifact, None,
            stage_name="c1_query_extraction", error_code="C1_NO_SAFE_QUERY_PARAMETER",
            error_fields=("bore_d",),
        )
        self.assertEqual(record["prompt_hashes"]["system_prompt_sha256"], artifact.system_prompt_sha256)
        self.assertEqual(record["prompt_hashes"]["user_template_sha256"], artifact.user_template_sha256)
        self.assertIsNone(record["prompt_hashes"]["unavailable_reason"])

    def test_transport_error_can_carry_only_retention_metadata(self):
        from llm.transport import TransportError

        err = TransportError("invalid_json", 200, "redacted", {"retained": True, "body_sha256": "a" * 64})
        self.assertEqual(err.diagnostic_retention["retained"], True)
        self.assertNotIn("body", err.message)


if __name__ == "__main__":
    unittest.main()
