"""Dashboard insights calculated from synthetic transaction aggregates."""

from decimal import ROUND_HALF_UP, Decimal

from app.financial_tools.money import MoneyInput, as_decimal


def _trend_insight(
    category: str,
    history: dict[str, float],
) -> str | None:
    values = list(history.items())
    if len(values) < 2:
        return None

    (previous_month, previous), (latest_month, latest) = values[-2:]
    previous_value = as_decimal(previous)
    latest_value = as_decimal(latest)
    if previous_value == 0:
        return None

    change = ((latest_value - previous_value) / previous_value * 100).quantize(
        Decimal("1"),
        rounding=ROUND_HALF_UP,
    )
    direction = "increased" if change >= 0 else "decreased"
    return (
        f"Your {category} spending {direction} by approximately "
        f"{abs(int(change))}% from {previous_month} to {latest_month}."
    )


def generate_dashboard_insights(
    *,
    spending_history: dict[str, dict[str, float]],
    latest_categories: dict[str, float],
    monthly_income: MoneyInput,
    monthly_savings: MoneyInput,
) -> list[str]:
    insights: list[str] = []
    dining = spending_history.get("dining")
    if dining:
        trend = _trend_insight("dining", dining)
        if trend:
            insights.append(trend)

    if latest_categories:
        category, amount = max(latest_categories.items(), key=lambda item: item[1])
        insights.append(
            f"{category.title()} is your largest monthly spending category at "
            f"${amount:,.2f}."
        )

    income = as_decimal(monthly_income)
    savings = as_decimal(monthly_savings)
    if income > 0:
        savings_rate = (savings / income * 100).quantize(
            Decimal("1"),
            rounding=ROUND_HALF_UP,
        )
        insights.append(f"You are saving approximately {int(savings_rate)}% of monthly income.")

    return insights[:3]
