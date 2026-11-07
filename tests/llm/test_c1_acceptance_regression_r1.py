"""Acceptance-case regression for C1 retrieval assembly boundaries.

These tests exercise only deterministic input projection and RET-002 query
assembly. They do not call a model or alter the frozen retrieval semantics.
"""

from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_projection_and_index():
    from llm.runner import App001Runner
    from retrieval import RetrievalIndex
    from retrieval.config import DEFAULT_CONFIG_REL_PATH

    projection = App001Runner()._load_projection()
    index = RetrievalIndex.from_config(DEFAULT_CONFIG_REL_PATH, repo_root=REPO_ROOT)
    return projection, index


class C1AcceptanceRegressionR1(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.projection, cls.index = _load_projection_and_index()

    def test_a02_catalog_valid_bore_d_builds_reference_context(self):
        from llm.conditions import assemble_c1

        case = self.projection.case_by_id("APP001-A02-only-bore-d")
        result = assemble_c1(case, self.index)

        self.assertIsNone(result.blocked_reason)
        self.assertIsNone(result.error_code)
        self.assertEqual(result.bore_d_used_for_query, 24.0)
        self.assertEqual(len(result.candidate_source_ids), 3)
        self.assertIsNotNone(result.reference_context_sha256)
        self.assertTrue(result.reference_context)
        self.assertNotIn("expected_parameters", result.reference_context)
        self.assertNotIn("evaluator", result.reference_context.lower())

    def test_a04_missing_bore_d_blocks_without_label_fallback(self):
        from llm.conditions import assemble_c1

        case = self.projection.case_by_id("APP001-A04-missing-bore-d")
        result = assemble_c1(case, self.index)

        self.assertEqual(result.blocked_stage, "c1_query_extraction")
        self.assertEqual(result.error_code, "C1_NO_SAFE_QUERY_PARAMETER")
        self.assertEqual(result.error_fields, ("bore_d",))
        self.assertIsNone(result.bore_d_used_for_query)
        self.assertEqual(result.candidate_source_ids, ())
        self.assertIsNone(result.reference_context_sha256)

    def test_a07_out_of_catalog_bore_d_remains_schema_rejected(self):
        from llm.conditions import assemble_c1

        case = self.projection.case_by_id("APP001-A07-out-of-catalog-and-unsupported")
        result = assemble_c1(case, self.index)

        self.assertEqual(result.blocked_stage, "retrieval_query")
        self.assertEqual(result.error_code, "RETRIEVAL_SCHEMA_REJECTED")
        self.assertIn("bore_d", result.error_fields)
        self.assertEqual(result.bore_d_used_for_query, 75.0)
        self.assertEqual(result.candidate_source_ids, ())
        self.assertIsNone(result.reference_context)
        self.assertIsNone(result.reference_context_sha256)
        self.assertIn("BLOCKED_C1_RETRIEVAL_ERROR", result.blocked_reason)


if __name__ == "__main__":
    unittest.main()
