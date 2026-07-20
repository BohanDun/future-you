import pytest

from app.models.customer import CustomerProfile
from app.models.scenario import ParsedScenario
from app.services.simulation_service import run_simulation


def _goal(result, goal_id: str):
    return next(goal for goal in result.goalImpacts if goal.goalId == goal_id)


def test_laptop_purchase_demo(alex: CustomerProfile) -> None:
    result = run_simulation(
        alex,
        ParsedScenario(
            scenarioType="one_off_purchase",
            amount=2000,
            frequency="one_time",
            description="Laptop",
        ),
    )

    house = _goal(result, "house_deposit")
    assert result.before.balance == 8000
    assert result.after.balance == 6000
    assert result.before.monthlyCashFlow == result.after.monthlyCashFlow == 1350
    assert (house.monthsBefore, house.monthsAfter) == (18, 20)
    assert result.beforeRiskLevel == "Low"
    assert result.riskLevel == "Medium"
    assert result.recommendation.weeklyAmount == 40


def test_weekly_rent_increase_demo(alex: CustomerProfile) -> None:
    result = run_simulation(
        alex,
        ParsedScenario(
            scenarioType="recurring_expense",
            amount=100,
            frequency="weekly",
            description="Rent increase",
        ),
    )

    house = _goal(result, "house_deposit")
    assert result.after.balance == 8000
    assert result.after.monthlyCashFlow == 916.67
    assert (house.monthsBefore, house.monthsAfter) == (18, 26)
    assert result.riskLevel == "High"


def test_weekly_extra_savings_demo(alex: CustomerProfile) -> None:
    result = run_simulation(
        alex,
        ParsedScenario(
            scenarioType="extra_savings",
            amount=50,
            frequency="weekly",
            description="Extra savings",
        ),
    )

    house = _goal(result, "house_deposit")
    assert result.after.monthlyCashFlow == 1350
    assert (house.monthsBefore, house.monthsAfter) == (18, 14)
    assert house.monthlyContributionAfter == 916.67
    assert result.riskLevel == "Low"
    assert result.recommendation.weeklyAmount == 50


def test_extra_savings_can_target_emergency_fund(alex: CustomerProfile) -> None:
    result = run_simulation(
        alex,
        ParsedScenario(
            scenarioType="extra_savings",
            amount=50,
            frequency="weekly",
            description="Extra emergency savings",
            goalId="emergency_fund",
        ),
    )

    house = _goal(result, "house_deposit")
    emergency = _goal(result, "emergency_fund")
    assert (house.monthsBefore, house.monthsAfter) == (18, 18)
    assert (emergency.monthsBefore, emergency.monthsAfter) == (5, 3)
    assert emergency.monthlyContributionAfter == 566.67


def test_missing_amount_is_rejected(alex: CustomerProfile) -> None:
    with pytest.raises(ValueError, match="positive"):
        run_simulation(alex, ParsedScenario(scenarioType="one_off_purchase"))
