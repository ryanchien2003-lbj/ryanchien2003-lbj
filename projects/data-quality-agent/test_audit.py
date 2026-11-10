import json
from pathlib import Path
import unittest

import pandas as pd
from audit import CHECKS, audit, execute

ROOT = Path(__file__).resolve().parent


class AuditTests(unittest.TestCase):
    def setUp(self):
        self.orders = pd.read_csv(ROOT / "orders.csv", dtype=str, keep_default_na=False)
        self.customers = pd.read_csv(ROOT / "customers.csv", dtype=str)

    def test_fixture_findings_and_overlapping_counts(self):
        report = audit(self.orders, self.customers)
        self.assertTrue(report["complete"])
        found = {r["rule"]: r["csv_row_numbers"] for r in report["checks"]}
        self.assertEqual([3, 4], found["duplicate_order_ids"])
        self.assertEqual([5, 9], found["invalid_amounts"])
        self.assertEqual([8], found["missing_values"])
        self.assertEqual([6], found["orphan_customers"])
        self.assertEqual(7, report["distinct_flagged_rows"])

    def test_whitespace_and_non_finite_values(self):
        self.orders.loc[0, "customer_id"] = " "
        self.orders.loc[0, "amount"] = "inf"
        report = audit(self.orders, self.customers)
        findings = {r["rule"]: r for r in report["checks"]}
        self.assertIn(2, findings["missing_values"]["csv_row_numbers"])
        self.assertIn(2, findings["invalid_amounts"]["csv_row_numbers"])
        self.assertEqual(8, report["distinct_flagged_rows"])

    def test_model_round_trip_and_partial_report(self):
        def complete(messages):
            index = sum(message["role"] == "tool" for message in messages)
            name = "profile" if index == 0 else "check"
            args = {} if index == 0 else {"rule": CHECKS[index - 1]}
            return {"tool_calls": [{"id": f"call{index}", "type": "function",
                                   "function": {"name": name, "arguments": json.dumps(args)}}]}
        report = audit(self.orders, self.customers, complete)
        self.assertTrue(report["complete"])
        self.assertFalse(audit(self.orders, self.customers, lambda _: {})["complete"])

    def test_invalid_tool_is_rejected(self):
        result = execute("check", {"rule": "delete_data"}, self.orders, self.customers)
        self.assertIn("error", result)


if __name__ == "__main__":
    unittest.main()
