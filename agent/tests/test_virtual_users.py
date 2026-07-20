import pytest

from agent import generate_explanation, parse_financial_question
from agent.fallback import generate_mock_explanation
from agent.scenario_parser import parse_question_mock
from agent.tests.fixtures.virtual_users import VIRTUAL_USERS
from app.services.simulation_service import run_simulation


def test_virtual_user_profiles_are_valid() -> None:
    assert len(VIRTUAL_USERS) == 3
    for user_id, customer in VIRTUAL_USERS.items():
        assert customer.customerId == user_id
        assert customer.monthlySavings == round(
            customer.monthlyIncome - customer.monthlyExpenses,
            2,
        )
        assert customer.currentBalance >= 0
        assert len(customer.goals) >= 2


@pytest.mark.parametrize(
    ("user_id", "question", "scenario_type", "amount"),
    [
        ("sam", "What happens if I buy a $500 phone?", "one_off_purchase", 500),
        ("jordan", "What if my rent increases by $50 per week?", "recurring_expense", 50),
        ("riley", "What if I save an extra $100 per week?", "extra_savings", 100),
    ],
)
def test_agent_parses_questions_for_virtual_users(
    user_id: str,
    question: str,
    scenario_type: str,
    amount: float,
) -> None:
    scenario = parse_financial_question(question)

    assert scenario.scenarioType == scenario_type
    assert scenario.amount == amount


@pytest.mark.parametrize(
    ("user_id", "balance_after", "risk_level"),
    [
        ("sam", -1100, "High"),
        ("jordan", 4500, "Medium"),
        ("riley", 20000, "Low"),
    ],
)
def test_laptop_scenario_risk_varies_by_virtual_user(
    user_id: str,
    balance_after: float,
    risk_level: str,
) -> None:
    customer = VIRTUAL_USERS[user_id]
    scenario = parse_question_mock("What happens if I buy a $2,000 laptop?")
    result = run_simulation(customer, scenario)

    assert result.after.balance == balance_after
    assert result.riskLevel == risk_level


def test_sam_small_purchase_still_reduces_balance(sam) -> None:
    scenario = parse_question_mock("Can I afford a $500 phone?")
    result = run_simulation(sam, scenario)

    assert result.before.balance == 900
    assert result.after.balance == 400
    assert result.riskLevel == "High"


def test_jordan_rent_increase_delays_house_goal(jordan) -> None:
    scenario = parse_question_mock("What if my rent increases by $50 per week?")
    result = run_simulation(jordan, scenario)

    house = next(g for g in result.goalImpacts if g.goalId == "house_deposit")
    assert house.monthsBefore == 31
    assert house.monthsAfter == 39
    assert result.riskLevel == "High"


def test_riley_extra_savings_accelerates_emergency_fund(riley) -> None:
    scenario = parse_question_mock(
        "What if I save an extra $100 per week for my emergency fund?"
    )
    scenario.goalId = "emergency_fund"
    result = run_simulation(riley, scenario)

    emergency = next(g for g in result.goalImpacts if g.goalId == "emergency_fund")
    assert emergency.monthsBefore == 4
    assert emergency.monthsAfter == 3
    assert result.riskLevel == "Low"


def test_mock_explanation_mentions_calculated_balance(virtual_user) -> None:
    scenario = parse_question_mock("What happens if I buy a $1,000 laptop?")
    result = run_simulation(virtual_user, scenario)
    explanation = generate_mock_explanation(virtual_user, scenario, result)

    assert f"${result.before.balance:,.2f}" in explanation
    assert f"${result.after.balance:,.2f}" in explanation
    assert result.riskLevel in explanation


def test_generate_explanation_pipeline_for_all_virtual_users() -> None:
    for customer in VIRTUAL_USERS.values():
        scenario = parse_financial_question("What happens if I buy a $1,000 laptop?")
        assert scenario.amount == 1000

        result = run_simulation(customer, scenario)
        explanation = generate_explanation(customer, scenario, result)

        assert explanation
        assert result.riskLevel in explanation
