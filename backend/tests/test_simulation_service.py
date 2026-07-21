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
    assert (house.monthsBefore, house.monthsAfter) == (18, 18)
    assert result.beforeRiskLevel == "Low"
    assert result.riskLevel == "Medium"
    assert result.recommendation.weeklyAmount == 40


def test_future_purchase_projects_cash_flow_and_goal_contributions(alex) -> None:
    result = run_simulation(
        alex,
        ParsedScenario(
            scenarioType="one_off_purchase",
            amount=3000,
            frequency="one_time",
            description="Japan trip",
            goalId="japan_holiday",
            horizonMonths=12,
            timingLabel="next year",
        ),
    )

    assert result.horizonMonths == 12
    assert result.atEventBefore is not None
    assert result.goalContributionsByEvent == 11_700
    assert result.atEventBefore.balance == 12_500
    assert result.fundedFromGoal == 3_000
    assert result.fundedFromBalance == 0
    assert result.after.balance == 12_500
    assert result.riskLevel == "Low"


def test_future_purchase_without_matching_goal_uses_projected_liquid_cash() -> None:
    customer = CustomerProfile(
        customerId="future-planner",
        name="Future Planner",
        currency="NZD",
        currentBalance=1000,
        monthlyIncome=6000,
        monthlyExpenses=2700,
        monthlySavings=3300,
        goals=[
            {
                "goalId": "emergency_one",
                "name": "Emergency Fund",
                "target": 5000,
                "current": 100,
                "monthlyContribution": 250,
            },
            {
                "goalId": "emergency_two",
                "name": "Emergency Fund",
                "target": 5000,
                "current": 100,
                "monthlyContribution": 300,
            },
        ],
    )
    result = run_simulation(
        customer,
        ParsedScenario(
            scenarioType="one_off_purchase",
            amount=3000,
            frequency="one_time",
            description="Trip to Japan",
            horizonMonths=12,
            timingLabel="next year",
        ),
    )

    assert result.atEventBefore is not None
    assert result.atEventBefore.balance == 34_000
    assert result.after.balance == 31_000
    assert result.fundedFromGoal == 0
    assert result.riskLevel == "Low"


def test_projection_flags_a_negative_balance_during_the_horizon() -> None:
    customer = CustomerProfile(
        customerId="tight-plan",
        name="Tight Plan",
        currency="NZD",
        currentBalance=100,
        monthlyIncome=0,
        monthlyExpenses=200,
        monthlySavings=-200,
        goals=[{
            "goalId": "short_goal",
            "name": "Short Goal",
            "target": 500,
            "current": 0,
            "monthlyContribution": 500,
        }],
    )
    result = run_simulation(
        customer,
        ParsedScenario(
            scenarioType="one_off_purchase",
            amount=50,
            description="Small purchase",
            horizonMonths=3,
        ),
    )

    assert result.minimumProjectedBalance == -500
    assert result.after.balance == -550
    assert result.riskLevel == "High"
    assert "negative" in result.riskReasons[0].lower()


def test_projection_does_not_fund_goals_without_positive_cash_flow() -> None:
    customer = CustomerProfile(
        customerId="zero-surplus",
        name="Zero Surplus",
        currency="NZD",
        currentBalance=1000,
        monthlyIncome=2700,
        monthlyExpenses=2700,
        monthlySavings=0,
        goals=[
            {
                "goalId": "emergency_one",
                "name": "Emergency Fund One",
                "target": 5000,
                "current": 100,
                "monthlyContribution": 300,
            },
            {
                "goalId": "emergency_two",
                "name": "Emergency Fund Two",
                "target": 5000,
                "current": 0,
                "monthlyContribution": 250,
            },
        ],
    )

    result = run_simulation(
        customer,
        ParsedScenario(
            scenarioType="one_off_purchase",
            amount=3000,
            description="Trip to Japan",
            horizonMonths=12,
        ),
    )

    assert result.goalContributionsByEvent == 0
    assert result.atEventBefore is not None
    assert result.atEventBefore.balance == 1000
    assert result.after.balance == -2000
    assert result.riskLevel == "High"


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


def test_future_rent_increase_starts_after_the_projection_horizon(alex) -> None:
    result = run_simulation(
        alex,
        ParsedScenario(
            scenarioType="recurring_expense",
            amount=100,
            frequency="weekly",
            description="Rent increase",
            horizonMonths=12,
            timingLabel="next year",
        ),
    )

    house = _goal(result, "house_deposit")
    assert result.atEventBefore is not None
    assert result.atEventBefore.balance == 12_500
    assert result.after.balance == 12_500
    assert result.after.monthlyCashFlow == 916.67
    assert (house.monthsBefore, house.monthsAfter) == (18, 18)
    assert result.riskLevel == "Low"


def test_recurring_expense_uses_unallocated_cash_before_delaying_goals() -> None:
    customer = CustomerProfile(
        customerId="surplus",
        name="Surplus Saver",
        currency="NZD",
        currentBalance=10_000,
        monthlyIncome=6_000,
        monthlyExpenses=3_000,
        monthlySavings=3_000,
        goals=[{
            "goalId": "deposit",
            "name": "Deposit",
            "target": 20_000,
            "current": 5_000,
            "monthlyContribution": 1_000,
        }],
    )

    result = run_simulation(
        customer,
        ParsedScenario(
            scenarioType="recurring_expense",
            amount=500,
            frequency="monthly",
            description="Insurance increase",
        ),
    )

    goal = _goal(result, "deposit")
    assert result.after.monthlyCashFlow == 2_500
    assert goal.monthlyContributionAfter == 1_000
    assert goal.monthsAfter == goal.monthsBefore == 15
    assert result.riskLevel == "Low"


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
    assert result.after.monthlyCashFlow == 1566.67
    assert (house.monthsBefore, house.monthsAfter) == (18, 18)
    assert house.monthlyContributionAfter == 700
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
    assert result.after.monthlyCashFlow == 1566.67


def test_missing_amount_is_rejected(alex: CustomerProfile) -> None:
    with pytest.raises(ValueError, match="positive"):
        run_simulation(alex, ParsedScenario(scenarioType="one_off_purchase"))


def test_scenario_rejects_a_frequency_that_conflicts_with_its_type() -> None:
    with pytest.raises(ValueError, match="recurring frequency"):
        ParsedScenario(
            scenarioType="recurring_expense",
            amount=100,
            frequency="one_time",
        )
