"""Load validated synthetic customer and transaction data from disk."""

import csv
import json
import os
import re
from collections import defaultdict
from pathlib import Path

from app.financial import calculate_monthly_cash_flow, generate_dashboard_insights
from app.financial.money import as_float
from app.models.customer import CustomerProfile, Transaction

DEFAULT_DATA_ROOT = Path(__file__).resolve().parents[2] / "data"
CUSTOMER_ID_PATTERN = re.compile(r"^[a-z0-9_-]+$")


def _data_root() -> Path:
    configured = os.getenv("FUTURE_YOU_DATA_DIR")
    return Path(configured) if configured else DEFAULT_DATA_ROOT


def _safe_customer_id(customer_id: str) -> str:
    normalized = customer_id.strip().lower()
    if not CUSTOMER_ID_PATTERN.fullmatch(normalized):
        raise ValueError("Invalid customer identifier")
    return normalized


def load_transactions(customer_id: str) -> list[Transaction]:
    normalized = _safe_customer_id(customer_id)
    path = _data_root() / "transactions" / f"{normalized}.csv"
    if not path.exists():
        return []

    with path.open(encoding="utf-8", newline="") as stream:
        return [Transaction.model_validate(row) for row in csv.DictReader(stream)]


def _aggregate_transactions(
    transactions: list[Transaction],
) -> tuple[float, float, dict[str, dict[str, float]], dict[str, float]]:
    if not transactions:
        return 0.0, 0.0, {}, {}

    latest_period = max((item.date.year, item.date.month) for item in transactions)
    latest_income = 0.0
    latest_expenses = 0.0
    latest_categories: dict[str, float] = defaultdict(float)
    history: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))

    for item in sorted(transactions, key=lambda value: (value.date, value.transactionId)):
        if item.direction != "expense":
            if (item.date.year, item.date.month) == latest_period:
                latest_income += item.amount
            continue

        month_name = item.date.strftime("%B")
        history[item.category][month_name] += item.amount
        if (item.date.year, item.date.month) == latest_period:
            latest_expenses += item.amount
            latest_categories[item.category] += item.amount

    rounded_history = {
        category: {month: round(amount, 2) for month, amount in months.items()}
        for category, months in history.items()
    }
    rounded_categories = {
        category: round(amount, 2) for category, amount in latest_categories.items()
    }
    return (
        round(latest_income, 2),
        round(latest_expenses, 2),
        rounded_history,
        rounded_categories,
    )


def load_customer_profile(customer_id: str) -> CustomerProfile | None:
    normalized = _safe_customer_id(customer_id)
    path = _data_root() / "customers" / f"{normalized}.json"
    if not path.exists():
        return None

    with path.open(encoding="utf-8") as stream:
        customer_data = json.load(stream)

    transactions = load_transactions(normalized)
    income, expenses, spending_history, categories = _aggregate_transactions(transactions)
    if transactions:
        customer_data["monthlyIncome"] = income
        customer_data["monthlyExpenses"] = expenses
        customer_data["monthlySavings"] = as_float(
            calculate_monthly_cash_flow(income, expenses)
        )
        customer_data["spending"] = spending_history
        customer_data["spendingCategories"] = categories
        customer_data["insights"] = generate_dashboard_insights(
            spending_history=spending_history,
            latest_categories=categories,
            monthly_income=income,
            monthly_savings=customer_data["monthlySavings"],
        )

    return CustomerProfile.model_validate(customer_data)
