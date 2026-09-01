import pytest

from app.models.agent_action import (
    CreateGoalOperation,
    GoalValues,
    SetGoalOperation,
    SetProfileOperation,
)
from app.services.agent_action_service import apply_agent_operations


def test_profile_operation_allows_negative_monthly_savings(alex) -> None:
    updated = apply_agent_operations(
        alex,
        [SetProfileOperation(
            operation="set",
            resource="profile",
            field="monthlyExpenses",
            value=alex.monthlyIncome + 500,
        )],
    )

    assert updated.monthlySavings == -500
    assert updated.spendingCategories == {}
    assert updated.insights == [
        "Update your spending categories to match the new monthly expenses."
    ]


def test_income_change_recalculates_dashboard_savings_insight(alex) -> None:
    updated = apply_agent_operations(
        alex,
        [SetProfileOperation(
            operation="set",
            resource="profile",
            field="monthlyIncome",
            value=7700,
        )],
    )

    assert updated.monthlySavings == 3850
    assert updated.spendingCategories == alex.spendingCategories
    assert updated.insights[-1] == (
        "You are saving approximately 50% of monthly income."
    )


def test_expense_change_invalidates_categories_regardless_of_operation_order(alex) -> None:
    updated = apply_agent_operations(
        alex,
        [
            SetProfileOperation(
                operation="set",
                resource="profile",
                field="monthlyExpenses",
                value=4000,
            ),
            SetProfileOperation(
                operation="set",
                resource="profile",
                field="monthlyIncome",
                value=6000,
            ),
        ],
    )

    assert updated.monthlySavings == 2000
    assert updated.spendingCategories == {}
    assert updated.insights == [
        "Update your spending categories to match the new monthly expenses."
    ]


def test_goal_operation_allows_zero_contribution(alex) -> None:
    goal = alex.goals[0]
    updated = apply_agent_operations(
        alex,
        [SetGoalOperation(
            operation="set",
            resource="goal",
            resourceId=goal.goalId,
            field="monthlyContribution",
            value=0,
        )],
    )

    assert updated.goals[0].monthlyContribution == 0


def test_goal_operation_allows_saved_amount_above_target(alex) -> None:
    goal = alex.goals[0]
    updated = apply_agent_operations(
        alex,
        [SetGoalOperation(
            operation="set",
            resource="goal",
            resourceId=goal.goalId,
            field="current",
            value=goal.target + 100,
        )],
    )

    assert updated.goals[0].current == goal.target + 100


def test_create_goal_rejects_generic_duplicate_name(alex) -> None:
    with pytest.raises(ValueError, match="already exists"):
        apply_agent_operations(
            alex,
            [CreateGoalOperation(
                operation="create",
                resource="goal",
                values=GoalValues(
                    name="Emergency",
                    target=5000,
                    current=0,
                    monthlyContribution=250,
                ),
            )],
        )


def test_rename_goal_rejects_generic_duplicate_name(alex) -> None:
    house = alex.goals[0]
    with pytest.raises(ValueError, match="already exists"):
        apply_agent_operations(
            alex,
            [SetGoalOperation(
                operation="set",
                resource="goal",
                resourceId=house.goalId,
                field="name",
                value="Emergency",
            )],
        )
