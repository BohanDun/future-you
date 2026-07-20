from decimal import Decimal

import pytest

from app.financial.calculations import (
    apply_extra_savings,
    apply_one_time_purchase,
    apply_recurring_expense,
    calculate_goal_completion_months,
    calculate_monthly_cash_flow,
    convert_to_monthly,
)


def test_monthly_cash_flow() -> None:
    assert calculate_monthly_cash_flow(5200, 3850) == Decimal("1350.00")


@pytest.mark.parametrize(
    ("target", "current", "contribution", "expected"),
    [
        (20000, 8000, 700, 18),
        (5000, 5000, 350, 0),
        (5000, 5500, 350, 0),
        (5000, 1000, 0, None),
    ],
)
def test_goal_completion_months(
    target: float,
    current: float,
    contribution: float,
    expected: int | None,
) -> None:
    assert calculate_goal_completion_months(target, current, contribution) == expected


def test_one_time_purchase_can_reveal_negative_balance() -> None:
    assert apply_one_time_purchase(8000, 2000) == Decimal("6000.00")
    assert apply_one_time_purchase(8000, 9000) == Decimal("-1000.00")


@pytest.mark.parametrize(
    ("amount", "frequency", "expected"),
    [
        (50, "weekly", Decimal("216.67")),
        (600, "monthly", Decimal("600.00")),
        (1200, "yearly", Decimal("100.00")),
    ],
)
def test_frequency_conversion(amount: float, frequency: str, expected: Decimal) -> None:
    assert convert_to_monthly(amount, frequency) == expected


def test_recurring_expense_and_extra_savings() -> None:
    monthly_cost, after_expense = apply_recurring_expense(1350, 100, "weekly")
    extra_monthly, after_contribution = apply_extra_savings(700, 50, "weekly")

    assert monthly_cost == Decimal("433.33")
    assert after_expense == Decimal("916.67")
    assert extra_monthly == Decimal("216.67")
    assert after_contribution == Decimal("916.67")


def test_negative_input_is_rejected() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        apply_one_time_purchase(8000, -1)
