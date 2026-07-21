from app.data import load_customer_profile, load_transactions
from app.services.customer_service import _refresh_dashboard_insights


def test_alex_profile_is_derived_from_transactions() -> None:
    customer = load_customer_profile("alex")

    assert customer is not None
    assert customer.monthlyIncome == 5200
    assert customer.monthlyExpenses == 3850
    assert customer.monthlySavings == 1350
    assert sum(customer.spendingCategories.values()) == 3850
    assert customer.spending["dining"] == {
        "April": 310,
        "May": 356,
        "June": 420,
    }


def test_dashboard_insights_use_latest_two_months() -> None:
    customer = load_customer_profile("alex")

    assert customer is not None
    assert customer.insights == [
        "Your dining spending increased by approximately 18% from May to June.",
        "Housing is your largest monthly spending category at $1,800.00.",
        "You are saving approximately 26% of monthly income.",
    ]


def test_synthetic_transaction_dataset() -> None:
    transactions = load_transactions("alex")

    assert len(transactions) == 19
    assert all(item.customerId == "alex" for item in transactions)
    assert {item.direction for item in transactions} == {"income", "expense"}


def test_unknown_customer_returns_none() -> None:
    assert load_customer_profile("missing") is None


def test_loaded_profile_insights_are_refreshed_from_current_income(alex) -> None:
    changed = alex.model_copy(update={
        "monthlyIncome": 7700,
        "monthlySavings": 3850,
        "insights": ["stale insight"],
    })

    refreshed = _refresh_dashboard_insights(changed)

    assert refreshed.insights[-1] == (
        "You are saving approximately 50% of monthly income."
    )
    assert "stale insight" not in refreshed.insights
