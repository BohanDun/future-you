import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_customer_endpoint_returns_person_two_data() -> None:
    response = client.get("/customer/alex")

    assert response.status_code == 200
    body = response.json()
    assert body["monthlySavings"] == 1350
    assert body["spendingCategories"]["housing"] == 1800
    assert len(body["insights"]) == 3


def test_simulate_endpoint_returns_all_goal_impacts() -> None:
    response = client.post(
        "/simulate",
        json={
            "customerId": "alex",
            "question": "What happens if I buy a $2,000 laptop?",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["result"]["after"]["balance"] == 6000
    assert body["result"]["riskLevel"] == "Medium"
    assert len(body["result"]["goalImpacts"]) == 3
    assert "$8,000.00 to $6,000.00" in body["explanation"]
    assert "delayed by 2 months" in body["explanation"]


def test_afford_question_with_explicit_amount_is_supported() -> None:
    response = client.post(
        "/simulate",
        json={
            "customerId": "alex",
            "question": "Can I afford a $3,000 trip to Japan next year?",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["scenario"]["scenarioType"] == "one_off_purchase"
    assert body["scenario"]["amount"] == 3000
    assert body["scenario"]["goalId"] == "japan_holiday"
    goals = {goal["goalId"]: goal for goal in body["result"]["goalImpacts"]}
    assert goals["house_deposit"]["monthsAfter"] == 18
    assert goals["japan_holiday"]["monthsBefore"] == 6
    assert goals["japan_holiday"]["monthsAfter"] == 10
    assert "Japan Holiday is delayed by 4 months" in body["explanation"]


def test_extra_savings_can_target_named_goal_through_api() -> None:
    response = client.post(
        "/simulate",
        json={
            "customerId": "alex",
            "question": "What if I save an extra $50 per week for my emergency fund?",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["scenario"]["goalId"] == "emergency_fund"
    goals = {goal["goalId"]: goal for goal in body["result"]["goalImpacts"]}
    assert goals["house_deposit"]["monthsAfter"] == 18
    assert goals["emergency_fund"]["monthsAfter"] == 3


def test_affordability_endpoint_returns_decision_boundaries() -> None:
    response = client.get(
        "/customer/alex/affordability",
        params={"goalId": "house_deposit"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["lowRiskLimit"] == 300
    assert body["mediumRiskLimit"] == 4100
    assert body["highRiskStartsAt"] == 4100.01


def test_stress_test_endpoint_models_income_loss() -> None:
    response = client.post(
        "/stress-test",
        json={"customerId": "alex", "incomeLossMonths": 2},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["balanceAfter"] == 300
    assert body["riskLevel"] == "High"
    assert len(body["goalImpacts"]) == 3


def test_goal_optimizer_endpoint_preserves_monthly_savings_budget() -> None:
    response = client.post(
        "/optimize-goals",
        json={
            "customerId": "alex",
            "priorityGoalId": "house_deposit",
            "targetMonths": 12,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["feasible"] is True
    assert sum(
        allocation["monthlyContributionAfter"]
        for allocation in body["allocations"]
    ) == 1350


def test_zero_amount_is_rejected() -> None:
    response = client.post(
        "/simulate",
        json={"customerId": "alex", "question": "What if I buy a $0 laptop?"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "A positive financial amount is required"


@pytest.mark.parametrize(
    ("question", "cash_flow", "house_months", "risk"),
    [
        ("What if my rent increases by $100 per week?", 916.67, 26, "High"),
        ("What if I save an extra $50 per week?", 1350, 14, "Low"),
    ],
)
def test_simulate_endpoint_core_recurring_scenarios(
    question: str,
    cash_flow: float,
    house_months: int,
    risk: str,
) -> None:
    response = client.post(
        "/simulate",
        json={"customerId": "alex", "question": question},
    )

    assert response.status_code == 200
    result = response.json()["result"]
    house = next(
        goal for goal in result["goalImpacts"] if goal["goalId"] == "house_deposit"
    )
    assert result["after"]["monthlyCashFlow"] == cash_flow
    assert house["monthsAfter"] == house_months
    assert result["riskLevel"] == risk
