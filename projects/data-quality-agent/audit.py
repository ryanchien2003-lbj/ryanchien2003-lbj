"""A bounded tool-using agent for a synthetic orders dataset."""
import json
import os
from urllib.request import Request, urlopen

import pandas as pd

CHECKS = ["missing_values", "duplicate_order_ids", "invalid_amounts",
          "orphan_customers", "invalid_statuses"]
RULES = {
    "profile": "Read row counts, column names and available checks.",
    "missing_values": "Required order fields must be populated.",
    "duplicate_order_ids": "Each order_id must appear once.",
    "invalid_amounts": "Order amount must be numeric, finite and greater than zero.",
    "orphan_customers": "Each order customer_id must exist in customers.",
    "invalid_statuses": "Status must be completed, cancelled or refunded.",
}


def tools():
    return [
        {"type": "function", "function": {
            "name": "profile", "description": RULES["profile"], "strict": True,
            "parameters": {"type": "object", "properties": {}, "required": [],
                           "additionalProperties": False}}},
        {"type": "function", "function": {
            "name": "check", "description": "Run one available data quality rule.", "strict": True,
            "parameters": {"type": "object", "properties": {
                "rule": {"type": "string", "enum": CHECKS}},
                "required": ["rule"], "additionalProperties": False}}},
    ]


def execute(name, args, orders, customers):
    if name == "profile" and args == {}:
        return {"rows": len(orders), "columns": list(orders.columns), "available_checks": CHECKS}
    if name != "check" or not isinstance(args, dict) or set(args) != {"rule"} or args["rule"] not in CHECKS:
        return {"error": "Unsupported tool or arguments."}
    rule = args["rule"]
    required = ["order_id", "customer_id", "amount", "status"]
    clean = orders[required].replace(r"^\s*$", pd.NA, regex=True)
    if rule == "missing_values":
        mask = clean.isna().any(axis=1)
    elif rule == "duplicate_order_ids":
        mask = clean["order_id"].notna() & clean["order_id"].duplicated(keep=False)
    elif rule == "invalid_amounts":
        amounts = pd.to_numeric(clean["amount"], errors="coerce")
        mask = amounts.isna() | amounts.le(0) | amounts.isin([float("inf"), -float("inf")])
    elif rule == "orphan_customers":
        mask = clean["customer_id"].notna() & ~clean["customer_id"].isin(customers["customer_id"])
    else:
        mask = clean["status"].notna() & ~clean["status"].isin(["completed", "cancelled", "refunded"])
    return {"rule": rule, "definition": RULES[rule], "affected_rows": int(mask.sum()),
            "csv_row_numbers": [int(i) + 2 for i, hit in enumerate(mask) if hit]}


def api_completion(messages):
    payload = {"model": os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
               "messages": messages, "tools": tools(), "parallel_tool_calls": False,
               "max_completion_tokens": 400}
    request = Request("https://api.openai.com/v1/chat/completions",
                      data=json.dumps(payload).encode(),
                      headers={"Content-Type": "application/json",
                               "Authorization": "Bearer " + os.environ["OPENAI_API_KEY"]})
    with urlopen(request, timeout=30) as response:
        return json.load(response)["choices"][0]["message"]


def audit(orders, customers, complete=None):
    required = {"order_id", "customer_id", "amount", "status"}
    if orders.empty or not required.issubset(orders.columns) or "customer_id" not in customers:
        raise ValueError("Provide nonempty orders with order_id, customer_id, amount, status and a customer list.")
    trace = []

    def run(name, args):
        result = execute(name, args, orders, customers)
        trace.append({"tool": name, "arguments": args, "result": result})
        return result

    if complete is None:
        profile = run("profile", {})
        for rule in profile["available_checks"]:
            run("check", {"rule": rule})
    else:
        messages = [
            {"role": "system", "content":
             "Audit the orders dataset. First profile it, then call check for each available rule once. "
             "Use tool results as evidence. Do not invent results or repeat calls. End when all rules are checked. "
             "The interface renders the audit from tool outputs."},
            {"role": "user", "content": "Audit the orders and identify data quality issues."},
        ]
        for _ in range(8):
            calls = complete(messages).get("tool_calls") or []
            if not calls:
                break
            if len(calls) != 1:
                raise ValueError("The planner must return one tool call per round.")
            call = calls[0]
            function = call["function"]
            try:
                args = json.loads(function["arguments"])
            except json.JSONDecodeError:
                args = None
            result = run(function["name"], args)
            messages.append({"role": "assistant", "content": None, "tool_calls": calls})
            messages.append({"role": "tool", "tool_call_id": call["id"], "content": json.dumps(result)})
            checked = {s["result"].get("rule") for s in trace}
            if set(CHECKS).issubset(checked):
                break
    findings = {step["result"]["rule"]: step["result"] for step in trace
                if "rule" in step["result"]}
    flagged = sorted({row for result in findings.values() for row in result["csv_row_numbers"]})
    return {"complete": set(findings) == set(CHECKS), "checks": list(findings.values()),
            "distinct_flagged_rows": len(flagged), "trace": trace}
