"""Calendar-month purchase retention computed in SQLite."""
from contextlib import closing
from datetime import date
from pathlib import Path
import random
import sqlite3

import pandas as pd

ROOT = Path(__file__).resolve().parent


def sample_orders():
    rng = random.Random(42)
    rows = []
    for customer in range(1, 301):
        first_month = rng.randint(1, 6)
        for month in range(first_month, 9):
            if month != first_month and rng.random() >= max(0.2, 0.64 - 0.055 * (month - first_month)):
                continue
            for _ in range(rng.randint(1, 3)):
                rows.append([f"O{len(rows) + 1:05d}", f"C{customer:03d}",
                             date(2025, month, rng.randint(1, 28)).isoformat(),
                             rng.randint(1500, 20000) / 100, "completed"])
        rows.append([f"O{len(rows) + 1:05d}", f"C{customer:03d}", "2025-08-28",
                     35.0, "cancelled"])
    return pd.DataFrame(rows, columns=["order_id", "customer_id", "order_date", "amount", "status"])


def retention(orders, observation_month="2025-08-01"):
    orders = orders.copy()
    dates = pd.to_datetime(orders["order_date"], format="%Y-%m-%d", errors="raise")
    horizon = pd.Timestamp(observation_month)
    if horizon.day != 1:
        raise ValueError("Use the first day of the observation month.")
    if dates.isna().any() or orders["customer_id"].isna().any():
        raise ValueError("Every order must have a customer and a valid date.")
    if dates.ge(horizon + pd.offsets.MonthBegin(1)).any():
        raise ValueError("Orders extend beyond the observation month.")
    if orders["order_id"].isna().any() or orders["order_id"].duplicated().any():
        raise ValueError("Each order_id must be populated and unique.")
    orders["order_date"] = dates.dt.strftime("%Y-%m-%d")
    with closing(sqlite3.connect(":memory:")) as db:
        orders.to_sql("orders", db, index=False)
        return pd.read_sql_query((ROOT / "cohort.sql").read_text(encoding="utf-8-sig"),
                                 db, params={"observation_month": horizon.strftime("%Y-%m-%d")})


if __name__ == "__main__":
    orders = sample_orders()
    orders.to_csv(ROOT / "orders.csv", index=False)
    result = retention(orders)
    result.to_csv(ROOT / "cohort-results.csv", index=False)
    print(result.to_string(index=False))
