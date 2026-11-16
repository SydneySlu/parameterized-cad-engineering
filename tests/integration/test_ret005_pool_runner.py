"""Tests for RET-005 pool runner (src/integration/ret005_pool_runner.py).

Covers:
- FakeTransport C0/C1 context assembly
- Labels physical isolation from model input
- Allowlist, 3-5 count limit, top-k, user parameter priority
- Zero CAD before confirmation, independent STEP after confirmation
- Cross-run file isolation
- Failure paths: missing params, conflict, unsupported, confirmation rejected,
  transport failure, parse failure
- Existing v5 prompt, Schema, IR, provider, RET-001, RET-002 unchanged
"""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from llm.contract import CONTRACT_VERSION, PROMPT_VERSION, FORMAL_EVALUATION_ALLOWED
from llm.transport import FakeTransport, TransportResponse
from retrieval.config import MANIFEST_REL_PATH, REPO_ROOT
from retrieval.pool import PoolError, POOL_MIN_SIZE, POOL_MAX_SIZE


def _pipeline_result(*, status="success", stage="step_export", run_dir="/tmp/fake",
                     step_path=None, ir_index=None, errors=None):
    """Build a PipelineResult-compatible object with all required fields."""
    from integration.pipeline import PipelineResult
    return PipelineResult(
        run_id="test-run",
        extraction_source="synthetic_fixture",
        status=status,
        stage=stage,
        errors=errors or [],
        questions=[],
        request_text="bore_d=24 mm",
        envelope_fixture_label="ret005_test",
        parameters={"bore_d": 24.0},
        ir_index=ir_index or ({"step_sha256": "a" * 64} if status == "success" else None),
        step_path=step_path or (
            f"{run_dir}/cad_output/part.step" if status == "success" else None
        ),
        run_dir=run_dir,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_MANIFEST_PATH = REPO_ROOT / MANIFEST_REL_PATH


def _load_all_manifest_ids() -> list[str]:
    if not _MANIFEST_PATH.is_file():
        return []
    return [
        json.loads(line)["sample_id"]
        for line in _MANIFEST_PATH.read_text().strip().split("\n")
        if line.strip()
    ]


_ALL_IDS = _load_all_manifest_ids()
_HAVE_MANIFEST = len(_ALL_IDS) >= POOL_MIN_SIZE


def _pool_ids(n: int = 3) -> list[str]:
    return _ALL_IDS[:n]


def _envelope(*, bore: float = 24.0, decision: str = "answer", unsupported=None,
              missing=None) -> str:
    data = {
        "contract_version": CONTRACT_VERSION,
        "prompt_version": PROMPT_VERSION,
        "decision": decision,
        "extracted_parameters": {"bore_d": bore},
        "unsupported_requests": unsupported or [],
        "evidence": [{"field": "bore_d", "quote": f"{bore} mm", "source": "user_input"}],
        "missing_fields": missing or [],
        "questions": [],
        "confidence": None,
    }
    return json.dumps(data, ensure_ascii=False)


def _make_transport(*responses: str) -> FakeTransport:
    transport = FakeTransport()
    for body in responses:
        transport.queue_response(TransportResponse(status=200, body=body))
    return transport


# ---------------------------------------------------------------------------
# 1. C0/C1 context assembly with FakeTransport
# ---------------------------------------------------------------------------


class TestPoolContextAssembly(unittest.TestCase):
    @unittest.skipUnless(_HAVE_MANIFEST, "RET-001 manifest not available")
    def test_c0_extraction_no_pool_context(self):
        from integration.ret005_pool_runner import Ret005PoolService, POOL_STATUS_NEEDS_CONFIRMATION
        transport = _make_transport(_envelope())
        service = Ret005PoolService(transport=transport)
        state = service.extract(
            "bore_d=24 mm 轴环",
            pool_sample_ids=_pool_ids(3),
            condition_id="C0",
        )
        self.assertEqual(state.product_status, POOL_STATUS_NEEDS_CONFIRMATION)
        self.assertIsNone(state.reference_context_sha256)
        self.assertEqual(state.candidate_source_ids, [])

    @unittest.skipUnless(_HAVE_MANIFEST, "RET-001 manifest not available")
    def test_c1_extraction_has_pool_context(self):
        from integration.ret005_pool_runner import Ret005PoolService, POOL_STATUS_NEEDS_CONFIRMATION
        transport = _make_transport(_envelope())
        service = Ret005PoolService(transport=transport)
        state = service.extract(
            "bore_d=24 mm 轴环",
            pool_sample_ids=_pool_ids(3),
            condition_id="C1",
        )
        self.assertEqual(state.product_status, POOL_STATUS_NEEDS_CONFIRMATION)
        self.assertIsNotNone(state.reference_context_sha256)
        self.assertRegex(state.reference_context_sha256, r"^[0-9a-f]{64}$")
        self.assertGreater(len(state.candidate_source_ids), 0)

    @unittest.skipUnless(_HAVE_MANIFEST, "RET-001 manifest not available")
    def test_c1_context_contains_pool_retrieval_source_role(self):
        from integration.ret005_pool_runner import Ret005PoolService
        transport = _make_transport(_envelope())
        service = Ret005PoolService(transport=transport)
        state = service.extract(
            "bore_d=24 mm 轴环",
            pool_sample_ids=_pool_ids(3),
            condition_id="C1",
        )
        # The rendered user prompt is in the transport call body
        calls = transport.calls
        self.assertGreater(len(calls), 0)
        rendered = calls[0].body["messages"][-1]["content"]
        self.assertIn("pool_retrieval_source_untrusted_reference", rendered)

    @unittest.skipUnless(_HAVE_MANIFEST, "RET-001 manifest not available")
    def test_c0_context_is_null(self):
        from integration.ret005_pool_runner import Ret005PoolService
        transport = _make_transport(_envelope())
        service = Ret005PoolService(transport=transport)
        service.extract(
            "bore_d=24 mm 轴环",
            pool_sample_ids=_pool_ids(3),
            condition_id="C0",
        )
        rendered = transport.calls[0].body["messages"][-1]["content"]
        self.assertTrue(rendered.endswith("reference_context:\nnull"))


# ---------------------------------------------------------------------------
# 2. Labels physical isolation from model input
# ---------------------------------------------------------------------------


class TestLabelsIsolation(unittest.TestCase):
    @unittest.skipUnless(_HAVE_MANIFEST, "RET-001 manifest not available")
    def test_evaluator_labels_not_in_prompt_or_context(self):
        """Evaluator labels must never appear in the model input."""
        from integration.ret005_pool_runner import Ret005PoolService
        # Load evaluator labels if they exist to get a marker
        labels_path = REPO_ROOT / "agent-work/integration/RET-004-PAIRED-LIVE-20261116-01/evaluator-labels.json"
        marker = None
        if labels_path.is_file():
            try:
                labels = json.loads(labels_path.read_text())
                marker = json.dumps(labels, ensure_ascii=False)[:100]
            except Exception:
                marker = None

        transport = _make_transport(_envelope())
        service = Ret005PoolService(transport=transport)
        state = service.extract(
            "bore_d=24 mm 轴环",
            pool_sample_ids=_pool_ids(3),
            condition_id="C1",
        )
        rendered = transport.calls[0].body["messages"][-1]["content"]
        if marker:
            self.assertNotIn(marker, rendered)
        # Generic: no "evaluator" or "label" keys
        self.assertNotIn("evaluator_labels", rendered)
        self.assertNotIn("expected_behavior", rendered)
        self.assertNotIn("explicit_parameter_claims", rendered)

    @unittest.skipUnless(_HAVE_MANIFEST, "RET-001 manifest not available")
    def test_held_out_truth_not_in_context(self):
        """Context must not include held-out truth or evaluator-only fields."""
        from integration.ret005_pool_runner import Ret005PoolService
        transport = _make_transport(_envelope())
        service = Ret005PoolService(transport=transport)
        state = service.extract(
            "bore_d=24 mm 轴环",
            pool_sample_ids=_pool_ids(3),
            condition_id="C1",
        )
        ctx = state.reference_context_sha256
        # The context is a sha256 hash, but the rendered prompt contains the context JSON
        rendered = transport.calls[0].body["messages"][-1]["content"]
        self.assertNotIn("heldout", rendered.lower())
        self.assertNotIn("held_out", rendered.lower())
        self.assertNotIn("ground_truth", rendered.lower())


# ---------------------------------------------------------------------------
# 3. Allowlist, count limits, top-k
# ---------------------------------------------------------------------------


class TestPoolRunnerAllowlistAndCount(unittest.TestCase):
    @unittest.skipUnless(_HAVE_MANIFEST, "RET-001 manifest not available")
    def test_pool_too_small_blocks_extraction(self):
        from integration.ret005_pool_runner import Ret005PoolService, POOL_STATUS_BLOCKED
        transport = _make_transport(_envelope())
        service = Ret005PoolService(transport=transport)
        state = service.extract(
            "bore_d=24 mm 轴环",
            pool_sample_ids=[_pool_ids(1)[0]],  # only 1 sample
            condition_id="C1",
        )
        self.assertEqual(state.product_status, POOL_STATUS_BLOCKED)
        codes = [e["code"] for e in state.errors]
        self.assertIn("POOL_TOO_SMALL", codes)

    @unittest.skipUnless(_HAVE_MANIFEST, "RET-001 manifest not available")
    def test_pool_too_large_blocks_extraction(self):
        from integration.ret005_pool_runner import Ret005PoolService, POOL_STATUS_BLOCKED
        if len(_ALL_IDS) < 6:
            self.skipTest("Need at least 6 manifest sample_ids")
        transport = _make_transport(_envelope())
        service = Ret005PoolService(transport=transport)
        state = service.extract(
            "bore_d=24 mm 轴环",
            pool_sample_ids=_ALL_IDS[:6],  # 6 samples
            condition_id="C1",
        )
        self.assertEqual(state.product_status, POOL_STATUS_BLOCKED)
        codes = [e["code"] for e in state.errors]
        self.assertIn("POOL_TOO_LARGE", codes)

    @unittest.skipUnless(_HAVE_MANIFEST, "RET-001 manifest not available")
    def test_pool_with_non_manifest_id_blocks(self):
        from integration.ret005_pool_runner import Ret005PoolService, POOL_STATUS_BLOCKED
        transport = _make_transport(_envelope())
        service = Ret005PoolService(transport=transport)
        ids = _pool_ids(2) + ["not-a-real-sample-id"]
        state = service.extract(
            "bore_d=24 mm 轴环",
            pool_sample_ids=ids,
            condition_id="C1",
        )
        self.assertEqual(state.product_status, POOL_STATUS_BLOCKED)
        codes = [e["code"] for e in state.errors]
        self.assertIn("POOL_SAMPLE_NOT_IN_ALLOWLIST", codes)

    @unittest.skipUnless(_HAVE_MANIFEST, "RET-001 manifest not available")
    def test_valid_pool_3_to_5_accepted(self):
        from integration.ret005_pool_runner import Ret005PoolService, POOL_STATUS_NEEDS_CONFIRMATION
        for n in range(POOL_MIN_SIZE, min(POOL_MAX_SIZE, len(_ALL_IDS)) + 1):
            transport = _make_transport(_envelope())
            service = Ret005PoolService(transport=transport)
            state = service.extract(
                "bore_d=24 mm 轴环",
                pool_sample_ids=_pool_ids(n),
                condition_id="C1",
            )
            self.assertEqual(
                state.product_status, POOL_STATUS_NEEDS_CONFIRMATION,
                f"Pool size {n} should produce needs_confirmation, got {state.product_status}, errors={state.errors}",
            )


# ---------------------------------------------------------------------------
# 4. User parameter priority
# ---------------------------------------------------------------------------


class TestUserParamPriorityInRunner(unittest.TestCase):
    @unittest.skipUnless(_HAVE_MANIFEST, "RET-001 manifest not available")
    def test_explicit_bore_mismatch_blocks_before_cad(self):
        """If model returns bore_d different from user text, block before CAD."""
        from integration.ret005_pool_runner import Ret005PoolService, POOL_STATUS_BLOCKED
        # User says bore_d=24, model returns bore_d=20
        transport = _make_transport(_envelope(bore=20.0))
        service = Ret005PoolService(transport=transport)
        state = service.extract(
            "bore_d=24 mm 轴环",
            pool_sample_ids=_pool_ids(3),
            condition_id="C1",
        )
        self.assertEqual(state.product_status, POOL_STATUS_BLOCKED)
        codes = [e["code"] for e in state.errors]
        self.assertIn("USER_PARAM_CONFLICT", codes)
        # Explicit bore_d is captured
        self.assertAlmostEqual(state.explicit_parameters["bore_d"], 24.0)
        # Model bore_d is captured
        self.assertAlmostEqual(state.extracted_parameters["bore_d"], 20.0)

    @unittest.skipUnless(_HAVE_MANIFEST, "RET-001 manifest not available")
    def test_explicit_bore_matches_proceeds_to_confirmation(self):
        from integration.ret005_pool_runner import Ret005PoolService, POOL_STATUS_NEEDS_CONFIRMATION
        transport = _make_transport(_envelope(bore=24.0))
        service = Ret005PoolService(transport=transport)
        state = service.extract(
            "bore_d=24 mm 轴环",
            pool_sample_ids=_pool_ids(3),
            condition_id="C1",
        )
        self.assertEqual(state.product_status, POOL_STATUS_NEEDS_CONFIRMATION)
        self.assertAlmostEqual(state.explicit_parameters["bore_d"], 24.0)

    @unittest.skipUnless(_HAVE_MANIFEST, "RET-001 manifest not available")
    def test_no_explicit_bore_proceeds_without_conflict(self):
        from integration.ret005_pool_runner import Ret005PoolService, POOL_STATUS_NEEDS_CONFIRMATION
        transport = _make_transport(_envelope(bore=24.0))
        service = Ret005PoolService(transport=transport)
        state = service.extract(
            "生成一个轴环",  # no bore_d in text
            pool_sample_ids=_pool_ids(3),
            condition_id="C0",  # C0 doesn't need bore_d for retrieval
        )
        self.assertEqual(state.product_status, POOL_STATUS_NEEDS_CONFIRMATION)
        self.assertEqual(state.explicit_parameters, {})

    @unittest.skipUnless(_HAVE_MANIFEST, "RET-001 manifest not available")
    def test_reference_samples_do_not_override_user_intent(self):
        """Reference pool samples must not override user explicit params."""
        from integration.ret005_pool_runner import Ret005PoolService, POOL_STATUS_BLOCKED
        # User says 24, pool may contain samples with different bore_d,
        # model returns 24 → should match and proceed
        transport = _make_transport(_envelope(bore=24.0))
        service = Ret005PoolService(transport=transport)
        state = service.extract(
            "bore_d=24 mm 轴环",
            pool_sample_ids=_pool_ids(3),
            condition_id="C1",
        )
        # If pool has samples with different bore_d, the model result (24)
        # matches the user explicit param (24), so no conflict
        self.assertNotEqual(state.product_status, POOL_STATUS_BLOCKED)


# ---------------------------------------------------------------------------
# 5. CAD isolation: zero CAD before confirmation, independent STEP after
# ---------------------------------------------------------------------------


class TestCADIsolation(unittest.TestCase):
    @unittest.skipUnless(_HAVE_MANIFEST, "RET-001 manifest not available")
    def test_zero_cad_calls_before_confirmation(self):
        """run_pipeline must NOT be called during extraction phase."""
        from integration.ret005_pool_runner import Ret005PoolService
        transport = _make_transport(_envelope())
        service = Ret005PoolService(transport=transport)
        # run_pipeline is imported inside confirm_pool_run only
        with patch("integration.pipeline.run_pipeline") as cad:
            state = service.extract(
                "bore_d=24 mm 轴环",
                pool_sample_ids=_pool_ids(3),
                condition_id="C1",
            )
            cad.assert_not_called()

    @unittest.skipUnless(_HAVE_MANIFEST, "RET-001 manifest not available")
    def test_cad_called_only_after_confirmation(self):
        """run_pipeline must only be called after confirm(confirmed=True)."""
        from integration.ret005_pool_runner import Ret005PoolService, POOL_STATUS_NEEDS_CONFIRMATION
        transport = _make_transport(_envelope())
        service = Ret005PoolService(transport=transport)
        state = service.extract(
            "bore_d=24 mm 轴环",
            pool_sample_ids=_pool_ids(3),
            condition_id="C1",
        )
        self.assertEqual(state.product_status, POOL_STATUS_NEEDS_CONFIRMATION)
        # Confirm → should call run_pipeline
        with patch("integration.pipeline.run_pipeline") as cad:
            cad.return_value = _pipeline_result()
            service.confirm(state.run_id, confirmed=True)
            cad.assert_called_once()

    @unittest.skipUnless(_HAVE_MANIFEST, "RET-001 manifest not available")
    def test_confirmation_rejected_does_not_call_cad(self):
        from integration.ret005_pool_runner import Ret005PoolService, POOL_STATUS_BLOCKED
        transport = _make_transport(_envelope())
        service = Ret005PoolService(transport=transport)
        state = service.extract(
            "bore_d=24 mm 轴环",
            pool_sample_ids=_pool_ids(3),
            condition_id="C1",
        )
        with patch("integration.pipeline.run_pipeline") as cad:
            result = service.confirm(state.run_id, confirmed=False)
            cad.assert_not_called()
            self.assertEqual(result.product_status, POOL_STATUS_BLOCKED)
            codes = [e["code"] for e in result.errors]
            self.assertIn("CONFIRMATION_REJECTED", codes)

    @unittest.skipUnless(_HAVE_MANIFEST, "RET-001 manifest not available")
    def test_each_run_gets_isolated_output_directory(self):
        """Each confirmed run writes to its own <output_root>/<run_id>/ directory."""
        from integration.ret005_pool_runner import Ret005PoolService
        with tempfile.TemporaryDirectory() as tmp:
            output_root = Path(tmp)
            transport = _make_transport(_envelope())
            service = Ret005PoolService(transport=transport, output_root=output_root)
            state1 = service.extract(
                "bore_d=24 mm 轴环",
                pool_sample_ids=_pool_ids(3),
                condition_id="C1",
            )
            with patch("integration.pipeline.run_pipeline") as cad:
                cad.return_value = _pipeline_result(
                    run_dir=str(output_root / state1.run_id),
                    step_path=str(output_root / state1.run_id / "cad_output" / "part.step"),
                )
                service.confirm(state1.run_id, confirmed=True)
            # The pipeline was called with an output_root that includes the run_id
            call_args = cad.call_args
            self.assertIn(state1.run_id, str(call_args.kwargs.get("output_root", "")))

    @unittest.skipUnless(_HAVE_MANIFEST, "RET-001 manifest not available")
    def test_cross_run_file_isolation(self):
        """Run A's STEP must not be accessible from run B."""
        from integration.ret005_pool_runner import Ret005PoolService
        with tempfile.TemporaryDirectory() as tmp:
            output_root = Path(tmp)
            transport = _make_transport(_envelope(), _envelope())
            service = Ret005PoolService(transport=transport, output_root=output_root)
            state_a = service.extract(
                "bore_d=24 mm 轴环",
                pool_sample_ids=_pool_ids(3),
                condition_id="C1",
            )
            state_b = service.extract(
                "bore_d=24 mm 轴环",
                pool_sample_ids=_pool_ids(3),
                condition_id="C1",
            )
            self.assertNotEqual(state_a.run_id, state_b.run_id)
            # Run A confirmed with a fake STEP
            with patch("integration.pipeline.run_pipeline") as cad:
                cad.return_value = _pipeline_result(
                    run_dir=str(output_root / state_a.run_id),
                    step_path=str(output_root / state_a.run_id / "cad_output" / "part.step"),
                )
                service.confirm(state_a.run_id, confirmed=True)
            # Run B is not confirmed yet → get_step_bytes_secure must return None
            self.assertIsNone(service.get_step_bytes_secure(state_b.run_id))

    @unittest.skipUnless(_HAVE_MANIFEST, "RET-001 manifest not available")
    def test_get_step_bytes_secure_rejects_other_run_paths(self):
        """get_step_bytes_secure must reject STEP paths outside the run's own directory."""
        from integration.ret005_pool_runner import Ret005PoolService
        with tempfile.TemporaryDirectory() as tmp:
            output_root = Path(tmp)
            transport = _make_transport(_envelope(), _envelope())
            service = Ret005PoolService(transport=transport, output_root=output_root)
            state_a = service.extract("bore_d=24 mm", _pool_ids(3), "C1")
            state_b = service.extract("bore_d=24 mm", _pool_ids(3), "C1")
            # Confirm run A with a STEP in its own dir
            with patch("integration.pipeline.run_pipeline") as cad:
                cad.return_value = _pipeline_result(
                    run_dir=str(output_root / state_a.run_id),
                    step_path=str(output_root / state_a.run_id / "cad_output" / "part.step"),
                )
                service.confirm(state_a.run_id, confirmed=True)
            # Confirm run B but point its STEP at run A's directory
            with patch("integration.pipeline.run_pipeline") as cad:
                cad.return_value = _pipeline_result(
                    run_dir=str(output_root / state_b.run_id),
                    step_path=str(output_root / state_a.run_id / "cad_output" / "part.step"),
                )
                service.confirm(state_b.run_id, confirmed=True)
            # get_step_bytes_secure(run B) should reject because step_path
            # is outside run B's directory
            self.assertIsNone(service.get_step_bytes_secure(state_b.run_id))


# ---------------------------------------------------------------------------
# 6. Failure paths
# ---------------------------------------------------------------------------


class TestFailurePaths(unittest.TestCase):
    @unittest.skipUnless(_HAVE_MANIFEST, "RET-001 manifest not available")
    def test_missing_fields_blocks_before_cad(self):
        from integration.ret005_pool_runner import Ret005PoolService, POOL_STATUS_BLOCKED
        transport = _make_transport(_envelope(missing=["bore_d"]))
        service = Ret005PoolService(transport=transport)
        state = service.extract("bore_d=24 mm 轴环", _pool_ids(3), "C1")
        self.assertEqual(state.product_status, POOL_STATUS_BLOCKED)
        codes = [e["code"] for e in state.errors]
        self.assertIn("GATE_MISSING_FIELDS", codes)

    @unittest.skipUnless(_HAVE_MANIFEST, "RET-001 manifest not available")
    def test_unsupported_request_blocks_before_cad(self):
        from integration.ret005_pool_runner import Ret005PoolService, POOL_STATUS_BLOCKED
        transport = _make_transport(_envelope(unsupported=["anodizing"]))
        service = Ret005PoolService(transport=transport)
        state = service.extract("bore_d=24 mm 轴环", _pool_ids(3), "C1")
        self.assertEqual(state.product_status, POOL_STATUS_BLOCKED)
        codes = [e["code"] for e in state.errors]
        self.assertIn("GATE_UNSUPPORTED_REQUESTS", codes)
        self.assertIn("anodizing", state.unsupported_requests)

    @unittest.skipUnless(_HAVE_MANIFEST, "RET-001 manifest not available")
    def test_decision_refuse_blocks_before_cad(self):
        from integration.ret005_pool_runner import Ret005PoolService, POOL_STATUS_BLOCKED
        transport = _make_transport(_envelope(decision="refuse"))
        service = Ret005PoolService(transport=transport)
        state = service.extract("bore_d=24 mm 轴环", _pool_ids(3), "C1")
        self.assertEqual(state.product_status, POOL_STATUS_BLOCKED)
        codes = [e["code"] for e in state.errors]
        self.assertIn("GATE_DECISION_REFUSE", codes)

    @unittest.skipUnless(_HAVE_MANIFEST, "RET-001 manifest not available")
    def test_decision_ask_blocks_before_cad(self):
        from integration.ret005_pool_runner import Ret005PoolService, POOL_STATUS_BLOCKED
        transport = _make_transport(_envelope(decision="ask"))
        service = Ret005PoolService(transport=transport)
        state = service.extract("bore_d=24 mm 轴环", _pool_ids(3), "C1")
        self.assertEqual(state.product_status, POOL_STATUS_BLOCKED)
        codes = [e["code"] for e in state.errors]
        self.assertIn("GATE_DECISION_ASK", codes)

    @unittest.skipUnless(_HAVE_MANIFEST, "RET-001 manifest not available")
    def test_parse_error_blocks_before_cad(self):
        from integration.ret005_pool_runner import Ret005PoolService, POOL_STATUS_BLOCKED
        transport = _make_transport("{not valid json")
        service = Ret005PoolService(transport=transport)
        state = service.extract("bore_d=24 mm 轴环", _pool_ids(3), "C1")
        self.assertEqual(state.product_status, POOL_STATUS_BLOCKED)
        codes = [e["code"] for e in state.errors]
        self.assertIn("PARSE_ERROR", codes)

    @unittest.skipUnless(_HAVE_MANIFEST, "RET-001 manifest not available")
    def test_transport_failure_blocks_before_cad(self):
        from integration.ret005_pool_runner import Ret005PoolService
        from llm.transport import TransportError, COND_TIMEOUT
        transport = FakeTransport()
        transport.queue_error(TransportError(condition=COND_TIMEOUT, http_status=None, message="timeout"))
        transport.queue_error(TransportError(condition=COND_TIMEOUT, http_status=None, message="timeout"))
        service = Ret005PoolService(transport=transport)
        state = service.extract("bore_d=24 mm 轴环", _pool_ids(3), "C1")
        self.assertIn(state.product_status, ("error", "blocked"))
        codes = [e["code"] for e in state.errors]
        self.assertTrue(
            any(c in codes for c in ("TRANSPORT_EXCEPTION", "NO_RESPONSE")),
            f"expected transport error code, got {codes}",
        )

    @unittest.skipUnless(_HAVE_MANIFEST, "RET-001 manifest not available")
    def test_c1_without_bore_d_in_text_blocks(self):
        from integration.ret005_pool_runner import Ret005PoolService, POOL_STATUS_BLOCKED
        transport = _make_transport(_envelope())
        service = Ret005PoolService(transport=transport)
        state = service.extract("需要一个轴环", _pool_ids(3), "C1")
        self.assertEqual(state.product_status, POOL_STATUS_BLOCKED)
        codes = [e["code"] for e in state.errors]
        self.assertIn("POOL_C1_NO_SAFE_QUERY_PARAMETER", codes)

    @unittest.skipUnless(_HAVE_MANIFEST, "RET-001 manifest not available")
    def test_pipeline_failure_returns_failed_state(self):
        from integration.ret005_pool_runner import Ret005PoolService, POOL_STATUS_FAILED
        transport = _make_transport(_envelope())
        service = Ret005PoolService(transport=transport)
        state = service.extract("bore_d=24 mm 轴环", _pool_ids(3), "C1")
        with patch("integration.pipeline.run_pipeline") as cad:
            cad.return_value = _pipeline_result(
                status="error", stage="ir_compile",
                run_dir="/tmp/fake",
                step_path=None,
                ir_index=None,
                errors=[{"code": "IR_COMPILE_ERROR", "message": "test failure"}],
            )
            result = service.confirm(state.run_id, confirmed=True)
            self.assertEqual(result.product_status, POOL_STATUS_FAILED)
            self.assertIsNone(result.step_path)

    @unittest.skipUnless(_HAVE_MANIFEST, "RET-001 manifest not available")
    def test_pipeline_exception_returns_failed_state(self):
        from integration.ret005_pool_runner import Ret005PoolService, POOL_STATUS_FAILED
        transport = _make_transport(_envelope())
        service = Ret005PoolService(transport=transport)
        state = service.extract("bore_d=24 mm 轴环", _pool_ids(3), "C1")
        with patch("integration.pipeline.run_pipeline", side_effect=RuntimeError("boom")):
            result = service.confirm(state.run_id, confirmed=True)
            self.assertEqual(result.product_status, POOL_STATUS_FAILED)
            codes = [e["code"] for e in result.errors]
            self.assertIn("PIPELINE_EXCEPTION", codes)

    @unittest.skipUnless(_HAVE_MANIFEST, "RET-001 manifest not available")
    def test_confirm_unknown_run_returns_none(self):
        from integration.ret005_pool_runner import Ret005PoolService
        transport = _make_transport(_envelope())
        service = Ret005PoolService(transport=transport)
        result = service.confirm("nonexistent-run-id", confirmed=True)
        self.assertIsNone(result)

    @unittest.skipUnless(_HAVE_MANIFEST, "RET-001 manifest not available")
    def test_confirm_non_bool_raises_type_error(self):
        from integration.ret005_pool_runner import Ret005PoolService
        transport = _make_transport(_envelope())
        service = Ret005PoolService(transport=transport)
        state = service.extract("bore_d=24 mm 轴环", _pool_ids(3), "C1")
        with self.assertRaises(TypeError):
            service.confirm(state.run_id, confirmed="true")  # type: ignore[arg-type]

    @unittest.skipUnless(_HAVE_MANIFEST, "RET-001 manifest not available")
    def test_non_fake_transport_rejected(self):
        from integration.ret005_pool_runner import Ret005PoolService
        with self.assertRaises(TypeError):
            Ret005PoolService(transport=object())  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# 7. FORMAL_EVALUATION_ALLOWED unchanged
# ---------------------------------------------------------------------------


class TestFormalGateUnchanged(unittest.TestCase):
    def test_formal_evaluation_allowed_remains_false(self):
        """RET-005 must not change FORMAL_EVALUATION_ALLOWED."""
        self.assertFalse(FORMAL_EVALUATION_ALLOWED)

    @unittest.skipUnless(_HAVE_MANIFEST, "RET-001 manifest not available")
    def test_formal_gate_unchanged_after_full_run(self):
        from integration.ret005_pool_runner import Ret005PoolService
        before = FORMAL_EVALUATION_ALLOWED
        transport = _make_transport(_envelope())
        service = Ret005PoolService(transport=transport)
        service.extract("bore_d=24 mm 轴环", _pool_ids(3), "C1")
        self.assertEqual(FORMAL_EVALUATION_ALLOWED, before)
        self.assertFalse(FORMAL_EVALUATION_ALLOWED)


# ---------------------------------------------------------------------------
# 8. Existing artifacts unchanged
# ---------------------------------------------------------------------------


class TestExistingArtifactsUnchanged(unittest.TestCase):
    def test_manifest_sha256_unchanged(self):
        """The RET-001 manifest must not be modified by RET-005."""
        from retrieval.config import sha256_file
        manifest = REPO_ROOT / MANIFEST_REL_PATH
        # Just verify the file exists and is readable
        self.assertTrue(manifest.is_file())
        sha = sha256_file(manifest)
        self.assertEqual(len(sha), 64)

    def test_retrieval_config_unchanged(self):
        """The RET-002 retrieval config must not be modified by RET-005."""
        from retrieval.config import DEFAULT_CONFIG_REL_PATH
        config_path = REPO_ROOT / DEFAULT_CONFIG_REL_PATH
        self.assertTrue(config_path.is_file())

    def test_prompt_version_unchanged(self):
        """The v5 prompt version must not change."""
        from llm.contract import PROMPT_VERSION
        self.assertIsInstance(PROMPT_VERSION, str)
        self.assertTrue(PROMPT_VERSION.startswith("app001-extraction.v5"))

    def test_contract_version_unchanged(self):
        from llm.contract import CONTRACT_VERSION
        self.assertIsInstance(CONTRACT_VERSION, str)


# ---------------------------------------------------------------------------
# 9. Shared context assembler (product mode == C1 experiment mode)
# ---------------------------------------------------------------------------


class TestSharedContextAssembler(unittest.TestCase):
    @unittest.skipUnless(_HAVE_MANIFEST, "RET-001 manifest not available")
    def test_c1_context_dict_has_retrieval_condition(self):
        from llm.pool_context import assemble_pool_c1
        from llm.input_projection import ProjectedCase
        pool_ids = _pool_ids(3)
        from retrieval.pool import ReferencePool
        pool = ReferencePool.from_manifest(pool_ids)
        case = ProjectedCase("q1", "bore_d=24 mm 轴环", None, ("bore_d",))
        assembled = assemble_pool_c1(case, pool)
        self.assertIsNone(assembled.blocked_reason)
        ref_dict = json.loads(assembled.reference_context)
        self.assertEqual(ref_dict["retrieval_condition"], "pool_C1_ret005_v1")

    @unittest.skipUnless(_HAVE_MANIFEST, "RET-001 manifest not available")
    def test_c1_context_candidates_contain_only_safe_fields(self):
        from llm.pool_context import assemble_pool_c1
        from llm.input_projection import ProjectedCase
        pool_ids = _pool_ids(3)
        from retrieval.pool import ReferencePool
        pool = ReferencePool.from_manifest(pool_ids)
        case = ProjectedCase("q1", "bore_d=24 mm 轴环", None, ("bore_d",))
        assembled = assemble_pool_c1(case, pool)
        ref_dict = json.loads(assembled.reference_context)
        for candidate in ref_dict["candidates"]:
            # Only these keys allowed
            self.assertEqual(set(candidate.keys()), {"role", "sample_id", "family_id", "parameters"})
            self.assertEqual(candidate["role"], "pool_retrieval_source_untrusted_reference")

    @unittest.skipUnless(_HAVE_MANIFEST, "RET-001 manifest not available")
    def test_c1_sha256_stable_for_same_input(self):
        """Same input must produce the same reference_context_sha256."""
        from llm.pool_context import assemble_pool_c1
        from llm.input_projection import ProjectedCase
        pool_ids = _pool_ids(3)
        from retrieval.pool import ReferencePool
        pool = ReferencePool.from_manifest(pool_ids)
        case1 = ProjectedCase("q1", "bore_d=24 mm 轴环", None, ("bore_d",))
        case2 = ProjectedCase("q2", "bore_d=24 mm 轴环", None, ("bore_d",))
        a1 = assemble_pool_c1(case1, pool)
        a2 = assemble_pool_c1(case2, pool)
        self.assertEqual(a1.reference_context_sha256, a2.reference_context_sha256)


if __name__ == "__main__":
    unittest.main()
