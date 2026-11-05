"""Cost and usage calculation tests: cache hit/miss, peak/off-peak, missing
fields -> not_available, local has no cloud cost.
"""

import unittest

from src.llm.cost import classify_rate_period, compute_cloud_cost


class RatePeriodTests(unittest.TestCase):
    def test_weekday_peak_morning_is_peak(self):
        # 2026-11-05 is a Thursday; 09:30 Beijing = 01:30 UTC
        self.assertEqual(classify_rate_period("2026-11-05T01:30:00Z"), "peak")

    def test_weekday_evening_outside_peak_is_off_peak(self):
        # 19:00 Beijing = 11:00 UTC Thursday
        self.assertEqual(classify_rate_period("2026-11-05T11:00:00Z"), "off_peak")

    def test_weekend_is_off_peak(self):
        # 2026-11-07 is a Saturday; 10:00 Beijing = 02:00 UTC
        self.assertEqual(classify_rate_period("2026-11-07T02:00:00Z"), "off_peak")

    def test_force_period_override(self):
        self.assertEqual(classify_rate_period("2026-11-05T01:30:00Z", force_period="off_peak"), "off_peak")
        self.assertEqual(classify_rate_period("2026-11-07T02:00:00Z", force_period="peak"), "peak")


class CostComputationTests(unittest.TestCase):
    def test_peak_cost_from_full_usage(self):
        result = compute_cloud_cost(
            request_timestamp_utc="2026-11-05T01:30:00Z",
            prompt_tokens=40,
            cached_input_tokens=0,
            cache_miss_input_tokens=40,
            output_tokens=6,
        )
        self.assertFalse(result["not_available"])
        # peak: 0*0.04 + 40*2.00 + 6*8.00 = 80 + 48 = 128 / 1e6 = 0.000128
        self.assertAlmostEqual(result["cost_amount"], 0.000128, places=8)
        self.assertEqual(result["cost_currency"], "CNY")
        self.assertEqual(result["rate_period"], "peak")

    def test_off_peak_cost_from_full_usage(self):
        result = compute_cloud_cost(
            request_timestamp_utc="2026-11-05T11:00:00Z",
            prompt_tokens=40,
            cached_input_tokens=0,
            cache_miss_input_tokens=40,
            output_tokens=6,
        )
        self.assertFalse(result["not_available"])
        # off peak: 0*0.02 + 40*1.00 + 6*4.00 = 40 + 24 = 64 / 1e6 = 0.000064
        self.assertAlmostEqual(result["cost_amount"], 0.000064, places=8)
        self.assertEqual(result["rate_period"], "off_peak")

    def test_missing_usage_yields_not_available(self):
        result = compute_cloud_cost(
            request_timestamp_utc="2026-11-05T01:30:00Z",
            prompt_tokens=None,
            cached_input_tokens=None,
            cache_miss_input_tokens=None,
            output_tokens=6,
        )
        self.assertTrue(result["not_available"])
        self.assertIsNone(result["cost_amount"])

    def test_missing_output_yields_not_available(self):
        result = compute_cloud_cost(
            request_timestamp_utc="2026-11-05T01:30:00Z",
            prompt_tokens=40,
            cached_input_tokens=0,
            cache_miss_input_tokens=40,
            output_tokens=None,
        )
        self.assertTrue(result["not_available"])

    def test_cost_records_rate_card_source_and_date(self):
        result = compute_cloud_cost(
            request_timestamp_utc="2026-11-05T01:30:00Z",
            prompt_tokens=40,
            cached_input_tokens=0,
            cache_miss_input_tokens=40,
            output_tokens=6,
        )
        self.assertIn("api-docs.deepseek.com", result["cost_source"])
        self.assertEqual(result["rate_card_observed_date"], "2026-11-05")


if __name__ == "__main__":
    unittest.main()
