from app.models.customer import CustomerProfile
from app.services.planning_service import (
    calculate_affordability,
    calculate_financial_health,
    optimize_goal_allocation,
    run_stress_test,
)


def test_financial_health_score_is_explainable(alex: CustomerProfile) -> None:
    result = calculate_financial_health(alex)

    assert result.score == 77
    assert result.status == "Strong"
    assert result.savingsRatePercent == 25.96
    assert result.reserveMonths == 2.08
    assert result.goalProgressPercent == 50
    assert sum(component.maxScore for component in result.components) == 100
    assert "$3,550.00" in result.nextBestAction


def test_affordability_finds_low_and_medium_purchase_boundaries(
    alex: CustomerProfile,
) -> None:
    result = calculate_affordability(alex, "house_deposit")

    assert result.lowRiskLimit == 300
    assert result.mediumRiskLimit == 4100
    assert result.highRiskStartsAt == 4100.01
    assert result.lowRiskBoundaryReasons == [
        "Available balance covers less than two months of expenses."
    ]
    assert result.mediumRiskBoundaryReasons == [
        "A financial goal is delayed by 6 months."
    ]


def test_affordability_changes_with_the_selected_goal(alex: CustomerProfile) -> None:
    japan = calculate_affordability(alex, "japan_holiday")
    emergency = calculate_affordability(alex, "emergency_fund")

    assert japan.mediumRiskLimit == 4150
    assert emergency.mediumRiskLimit == 2000


def test_unexpected_expense_reduces_emergency_runway(alex: CustomerProfile) -> None:
    result = run_stress_test(
        alex,
        income_loss_months=0,
        unexpected_expense=2500,
    )

    assert result.balanceAfter == 5500
    assert result.runwayMonthsAfter == 1.43
    assert result.riskLevel == "Medium"


def test_income_loss_pauses_all_goal_timelines(alex: CustomerProfile) -> None:
    result = run_stress_test(
        alex,
        income_loss_months=2,
        unexpected_expense=0,
    )

    house = next(goal for goal in result.goalImpacts if goal.goalId == "house_deposit")
    assert result.balanceAfter == 300
    assert result.monthlyCashFlowDuringShock == -3850
    assert result.riskLevel == "High"
    assert (house.monthsBefore, house.monthsAfter) == (18, 20)


def test_goal_optimizer_reallocates_without_creating_new_savings(
    alex: CustomerProfile,
) -> None:
    result = optimize_goal_allocation(
        alex,
        priority_goal_id="house_deposit",
        target_months=12,
    )

    allocations = {item.goalId: item for item in result.allocations}
    assert result.feasible is True
    assert allocations["house_deposit"].monthlyContributionAfter == 1000
    assert allocations["house_deposit"].monthsAfter == 12
    assert sum(item.monthlyContributionAfter for item in result.allocations) == 1350


def test_goal_optimizer_reports_an_infeasible_deadline(alex: CustomerProfile) -> None:
    result = optimize_goal_allocation(
        alex,
        priority_goal_id="house_deposit",
        target_months=8,
    )

    assert result.feasible is False
    assert result.earliestPossibleMonths == 9
    assert "not feasible" in result.summary
