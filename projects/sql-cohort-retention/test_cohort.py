import unittest

import pandas as pd

from analysis import retention


class CohortTests(unittest.TestCase):
    def setUp(self):
        self.orders = pd.DataFrame([
            ["O1", "A", "2025-01-03", 10, "completed"],
            ["O2", "A", "2025-01-04", 20, "completed"],
            ["O3", "A", "2025-03-02", 15, "completed"],
            ["O4", "B", "2025-01-05", 25, "completed"],
            ["O5", "C", "2025-02-01", 5, "cancelled"],
            ["O6", "C", "2025-03-03", 30, "completed"],
        ], columns=["order_id", "customer_id", "order_date", "amount", "status"])

    def test_customer_grain_zero_activity_and_unobserved_months(self):
        result = retention(self.orders, "2025-03-01")
        jan = result[result["cohort_month"].eq("2025-01-01")]
        self.assertEqual([2, 0, 1], jan["active_customers"].tolist())
        self.assertEqual([1.0, 0.0, 0.5], jan["retention"].tolist())
        march = result[result["cohort_month"].eq("2025-03-01")]
        self.assertEqual([0], march["month_index"].tolist())
        self.assertEqual(1, march["cohort_size"].iloc[0])

    def test_duplicate_order_ids_fail(self):
        self.orders.loc[1, "order_id"] = "O1"
        with self.assertRaises(ValueError):
            retention(self.orders)

    def test_future_orders_and_invalid_dates_fail(self):
        with self.assertRaises(ValueError):
            retention(self.orders, "2025-02-01")
        self.orders.loc[0, "order_date"] = "bad"
        with self.assertRaises(ValueError):
            retention(self.orders)


if __name__ == "__main__":
    unittest.main()
