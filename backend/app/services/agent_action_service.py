import re

from app.financial_tools import generate_dashboard_insights
from app.models.agent_action import (
    AgentOperation,
    ChangePreview,
    CreateGoalOperation,
    SetGoalOperation,
    SetProfileOperation,
)
from app.models.customer import CustomerProfile, FinancialGoal


def _goal_id(name: str, existing_ids: set[str]) -> str:
    base = re.sub(r"[^a-z0-9]+", "_", name.strip().lower()).strip("_") or "goal"
    candidate = base
    suffix = 2
    while candidate in existing_ids:
        candidate = f"{base}_{suffix}"
        suffix += 1
    return candidate


def apply_agent_operations(
    profile: CustomerProfile,
    operations: list[AgentOperation],
) -> CustomerProfile:
    updated = profile.model_copy(deep=True)
    income_changed = False
    expenses_changed = False

    for item in operations:
        if isinstance(item, CreateGoalOperation):
            if len(updated.goals) >= 10:
                raise ValueError("A profile can have at most 10 goals")
            values = item.values
            duplicate_name = any(
                goal.name.casefold() == values.name.strip().casefold()
                for goal in updated.goals
            )
            if duplicate_name:
                raise ValueError("A goal with this name already exists")
            updated.goals.append(
                FinancialGoal(
                    goalId=_goal_id(values.name, {goal.goalId for goal in updated.goals}),
                    name=values.name.strip(),
                    target=values.target,
                    current=values.current,
                    monthlyContribution=values.monthlyContribution,
                )
            )
            continue

        if isinstance(item, SetProfileOperation):
            setattr(updated, item.field, item.value)
            if item.field == "monthlyIncome":
                income_changed = True
            if item.field == "monthlyExpenses":
                expenses_changed = True
                updated.spendingCategories = {}
            continue

        if isinstance(item, SetGoalOperation):
            goal = next((goal for goal in updated.goals if goal.goalId == item.resourceId), None)
            if goal is None:
                raise ValueError(f"Goal '{item.resourceId}' was not found")
            values = goal.model_dump()
            values[item.field] = item.value.strip() if isinstance(item.value, str) else item.value
            updated.goals[updated.goals.index(goal)] = FinancialGoal.model_validate(values)

    updated.monthlySavings = round(updated.monthlyIncome - updated.monthlyExpenses, 2)
    if expenses_changed:
        updated.insights = [
            "Update your spending categories to match the new monthly expenses."
        ]
    elif income_changed:
        updated.insights = generate_dashboard_insights(
            spending_history=updated.spending,
            latest_categories=updated.spendingCategories,
            monthly_income=updated.monthlyIncome,
            monthly_savings=updated.monthlySavings,
        )
    return CustomerProfile.model_validate(updated.model_dump())


def preview_agent_operations(
    profile: CustomerProfile,
    operations: list[AgentOperation],
) -> list[ChangePreview]:
    updated = apply_agent_operations(profile, operations)
    preview: list[ChangePreview] = []
    money_fields = {
        "currentBalance": "Current balance",
        "monthlyIncome": "Monthly income",
        "monthlyExpenses": "Monthly expenses",
        "monthlySavings": "Monthly savings",
    }
    for field, label in money_fields.items():
        before = getattr(profile, field)
        after = getattr(updated, field)
        if before != after:
            preview.append(ChangePreview(
                label=label,
                before=f"{profile.currency} {before:,.2f}",
                after=f"{updated.currency} {after:,.2f}",
            ))

    previous_goals = {goal.goalId: goal for goal in profile.goals}
    for goal in updated.goals:
        previous = previous_goals.get(goal.goalId)
        if previous is None:
            preview.append(ChangePreview(
                label=f"Add goal: {goal.name}",
                after=(
                    f"Target {profile.currency} {goal.target:,.2f}; "
                    f"saved {profile.currency} {goal.current:,.2f}; "
                    f"{profile.currency} {goal.monthlyContribution:,.2f}/month"
                ),
            ))
            continue
        for field, field_label in {
            "name": "Name",
            "target": "Target",
            "current": "Saved",
            "monthlyContribution": "Monthly contribution",
        }.items():
            before = getattr(previous, field)
            after = getattr(goal, field)
            if before == after:
                continue
            is_money = field != "name"
            preview.append(ChangePreview(
                label=f"{goal.name}: {field_label}",
                before=f"{profile.currency} {before:,.2f}" if is_money else str(before),
                after=f"{profile.currency} {after:,.2f}" if is_money else str(after),
            ))
    return preview
