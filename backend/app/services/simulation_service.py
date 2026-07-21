"""Adapt validated API models to the deterministic Person 2 financial tools."""

import math
from decimal import ROUND_CEILING, Decimal

from app.financial_tools import (
    apply_extra_savings,
    apply_one_time_purchase,
    apply_recurring_expense,
    assess_financial_risk,
    calculate_goal_completion_months,
    calculate_monthly_cash_flow,
)
from app.financial_tools.money import as_decimal, as_float, money
from app.models.customer import CustomerProfile, FinancialGoal
from app.models.scenario import ParsedScenario
from app.models.simulation import (
    FinancialSnapshot,
    GoalImpact,
    Recommendation,
    SimulationResult,
)


def _target_goal(
    customer: CustomerProfile,
    scenario: ParsedScenario,
    *,
    use_default: bool = False,
) -> FinancialGoal | None:
    if scenario.goalId:
        selected = next(
            (goal for goal in customer.goals if goal.goalId == scenario.goalId),
            None,
        )
        if selected:
            return selected

    description = (scenario.description or "").casefold()
    selected = next(
        (
            goal
            for goal in customer.goals
            if goal.name.casefold() in description
            or any(
                len(word) >= 4 and word in description
                for word in goal.name.casefold().split()
            )
        ),
        None,
    )
    if selected is not None:
        return selected
    return customer.goals[0] if use_default and customer.goals else None


def _project_to_horizon(
    customer: CustomerProfile,
    horizon_months: int,
) -> tuple[Decimal, dict[str, Decimal], Decimal, Decimal]:
    cash_flow = as_decimal(calculate_monthly_cash_flow(
        customer.monthlyIncome,
        customer.monthlyExpenses,
    ))
    liquid_balance = as_decimal(customer.currentBalance)
    minimum_balance = liquid_balance
    projected_goals = {
        goal.goalId: as_decimal(goal.current)
        for goal in customer.goals
    }
    total_contributed = Decimal("0")

    for _ in range(horizon_months):
        liquid_balance += cash_flow
        # Goal contributions are allocations of this month's positive surplus.
        # Do not fund them from an existing cash buffer or while cash flow is
        # negative; that would create savings by driving liquid cash below zero.
        available_for_goals = max(cash_flow, Decimal("0"))
        for goal in customer.goals:
            current = projected_goals[goal.goalId]
            remaining = max(as_decimal(goal.target) - current, Decimal("0"))
            contributed = min(
                as_decimal(goal.monthlyContribution),
                remaining,
                available_for_goals,
            )
            projected_goals[goal.goalId] = current + contributed
            liquid_balance -= contributed
            total_contributed += contributed
            available_for_goals -= contributed
        minimum_balance = min(minimum_balance, liquid_balance)

    return (
        money(liquid_balance),
        projected_goals,
        money(total_contributed),
        money(minimum_balance),
    )


def _goal_impacts(
    customer: CustomerProfile,
    scenario: ParsedScenario,
    monthly_delta: Decimal,
    projected_goals: dict[str, Decimal] | None = None,
) -> list[GoalImpact]:
    primary = _target_goal(
        customer,
        scenario,
        use_default=False,
    )
    impacts: list[GoalImpact] = []
    current_by_goal = {
        goal.goalId: (
            projected_goals[goal.goalId]
            if projected_goals is not None
            else as_decimal(goal.current)
        )
        for goal in customer.goals
    }
    active_contributions = sum(
        (
            as_decimal(goal.monthlyContribution)
            for goal in customer.goals
            if current_by_goal[goal.goalId] < as_decimal(goal.target)
        ),
        Decimal("0"),
    )
    recurring_scale = Decimal("1")
    if scenario.scenarioType == "recurring_expense" and active_contributions > 0:
        cash_flow_after = as_decimal(customer.monthlySavings) + monthly_delta
        available_for_goals = max(cash_flow_after, Decimal("0"))
        recurring_scale = min(
            available_for_goals / active_contributions,
            Decimal("1"),
        )

    for goal in customer.goals:
        current_after = as_decimal(goal.current)
        contribution_after = as_decimal(goal.monthlyContribution)

        if scenario.scenarioType == "recurring_expense":
            if current_by_goal[goal.goalId] >= as_decimal(goal.target):
                contribution_after = Decimal("0")
            else:
                contribution_after *= recurring_scale
        elif scenario.scenarioType == "extra_savings" and goal is primary:
            contribution_after += monthly_delta

        months_before = calculate_goal_completion_months(
            goal.target,
            goal.current,
            goal.monthlyContribution,
        )
        months_after = calculate_goal_completion_months(
            goal.target,
            current_after,
            contribution_after,
        )
        if projected_goals is not None and scenario.horizonMonths > 0:
            current_at_event = projected_goals[goal.goalId]
            if months_before is not None and months_before <= scenario.horizonMonths:
                months_after = months_before
            else:
                remaining_months = calculate_goal_completion_months(
                    goal.target,
                    current_at_event,
                    contribution_after,
                )
                months_after = (
                    None
                    if remaining_months is None
                    else scenario.horizonMonths + remaining_months
                )
        impacts.append(
            GoalImpact(
                goalId=goal.goalId,
                goalName=goal.name,
                monthsBefore=months_before,
                monthsAfter=months_after,
                monthlyContributionBefore=as_float(goal.monthlyContribution),
                monthlyContributionAfter=as_float(contribution_after),
                currentAtEvent=(
                    as_float(projected_goals[goal.goalId])
                    if projected_goals and goal.goalId in projected_goals
                    else None
                ),
            )
        )

    return impacts


def _goal_delay(impact: GoalImpact) -> int:
    if impact.monthsBefore is None:
        return 0
    if impact.monthsAfter is None:
        return math.inf
    return max(impact.monthsAfter - impact.monthsBefore, 0)


def _max_goal_delay(impacts: list[GoalImpact]) -> int:
    delays = [_goal_delay(impact) for impact in impacts]
    if not delays:
        return 0
    maximum = max(delays)
    return 999 if math.isinf(maximum) else int(maximum)


def _recommendation(
    scenario: ParsedScenario,
    risk_level: str,
    max_goal_delay: int,
    horizon_months: int = 0,
    balance_after: Decimal | None = None,
) -> Recommendation:
    amount = scenario.amount or 0
    if scenario.scenarioType == "one_off_purchase":
        if risk_level == "Low" and max_goal_delay == 0:
            timing = "future plan" if horizon_months > 0 else "current plan"
            return Recommendation(description=f"This purchase fits within the {timing}.")
        weekly_recovery = None
        recovery_amount = max(-(balance_after or Decimal("0")), Decimal("0"))
        if recovery_amount == 0 and amount > 0:
            recovery_amount = as_decimal(amount)
        weeks = max(horizon_months * 52 / 12, 52)
        if recovery_amount > 0:
            units = (
                recovery_amount / Decimal(str(weeks)) / Decimal("5")
            ).to_integral_value(rounding=ROUND_CEILING)
            weekly_recovery = as_float(units * Decimal("5"))
        description = (
            "Reduce discretionary spending temporarily to recover the goal delay."
            if max_goal_delay > 0
            else "Build a larger available-cash buffer before making the purchase."
        )
        return Recommendation(
            description=description,
            weeklyAmount=weekly_recovery,
        )
    if scenario.scenarioType == "recurring_expense":
        return Recommendation(
            description="Review recurring expenses before committing to the increase.",
            weeklyAmount=amount if scenario.frequency == "weekly" else None,
        )
    return Recommendation(
        description="Continue the additional savings plan.",
        weeklyAmount=amount if scenario.frequency == "weekly" else None,
    )


def run_simulation(
    customer: CustomerProfile,
    scenario: ParsedScenario,
) -> SimulationResult:
    if scenario.scenarioType == "unknown":
        raise ValueError("Unsupported scenario")
    if scenario.amount is None or scenario.amount <= 0:
        raise ValueError("A positive financial amount is required")

    cash_flow_before = calculate_monthly_cash_flow(
        customer.monthlyIncome,
        customer.monthlyExpenses,
    )
    balance_after = money(customer.currentBalance)
    at_event_before_balance = money(customer.currentBalance)
    cash_flow_after = cash_flow_before
    monthly_delta = Decimal("0")
    projected_goals: dict[str, Decimal] | None = None
    contributed_by_event = Decimal("0")
    funded_from_goal = Decimal("0")
    funded_from_balance = Decimal("0")
    minimum_projected_balance = money(customer.currentBalance)

    if scenario.scenarioType == "one_off_purchase" or scenario.horizonMonths > 0:
        (
            at_event_before_balance,
            projected_goals,
            contributed_by_event,
            minimum_projected_balance,
        ) = _project_to_horizon(customer, scenario.horizonMonths)
        balance_after = at_event_before_balance

    if scenario.scenarioType == "one_off_purchase":
        primary = _target_goal(customer, scenario)
        if primary is not None:
            funded_from_goal = min(
                projected_goals.get(primary.goalId, Decimal("0")),
                as_decimal(scenario.amount),
            )
        funded_from_balance = as_decimal(scenario.amount) - funded_from_goal
        balance_after = apply_one_time_purchase(
            at_event_before_balance,
            funded_from_balance,
        )
    elif scenario.scenarioType == "recurring_expense":
        frequency = scenario.frequency or "monthly"
        monthly_cost, cash_flow_after = apply_recurring_expense(
            cash_flow_before,
            scenario.amount,
            frequency,
        )
        monthly_delta = -monthly_cost
    elif scenario.scenarioType == "extra_savings":
        frequency = scenario.frequency or "monthly"
        primary = _target_goal(customer, scenario)
        current_contribution = primary.monthlyContribution if primary else 0
        extra_monthly, _ = apply_extra_savings(
            current_contribution,
            scenario.amount,
            frequency,
        )
        monthly_delta = extra_monthly
        cash_flow_after = money(as_decimal(cash_flow_before) + extra_monthly)
    else:
        raise ValueError("Unsupported scenario")

    goal_impacts = _goal_impacts(
        customer,
        scenario,
        monthly_delta,
        projected_goals=projected_goals,
    )
    primary = _target_goal(
        customer,
        scenario,
        use_default=False,
    )
    primary_impact = next(
        (impact for impact in goal_impacts if primary and impact.goalId == primary.goalId),
        None,
    )
    max_delay = _max_goal_delay(goal_impacts)

    risk_before = assess_financial_risk(
        monthly_cash_flow_before=cash_flow_before,
        monthly_cash_flow_after=cash_flow_before,
        available_balance_after=customer.currentBalance,
        monthly_expenses=customer.monthlyExpenses,
        max_goal_delay_months=0,
    )
    risk_after = assess_financial_risk(
        monthly_cash_flow_before=cash_flow_before,
        monthly_cash_flow_after=cash_flow_after,
        available_balance_after=balance_after,
        monthly_expenses=customer.monthlyExpenses,
        max_goal_delay_months=max_delay,
        minimum_projected_balance=minimum_projected_balance,
    )
    event_risk = assess_financial_risk(
        monthly_cash_flow_before=cash_flow_before,
        monthly_cash_flow_after=cash_flow_before,
        available_balance_after=at_event_before_balance,
        monthly_expenses=customer.monthlyExpenses,
        max_goal_delay_months=0,
        minimum_projected_balance=minimum_projected_balance,
    )

    before = FinancialSnapshot(
        balance=as_float(customer.currentBalance),
        monthlyCashFlow=as_float(cash_flow_before),
        goalMonths=primary_impact.monthsBefore if primary_impact else None,
    )
    after = FinancialSnapshot(
        balance=as_float(balance_after),
        monthlyCashFlow=as_float(cash_flow_after),
        goalMonths=primary_impact.monthsAfter if primary_impact else None,
    )
    at_event_before = FinancialSnapshot(
        balance=as_float(at_event_before_balance),
        monthlyCashFlow=as_float(cash_flow_before),
        goalMonths=primary_impact.monthsBefore if primary_impact else None,
    )
    return SimulationResult(
        before=before,
        after=after,
        beforeRiskLevel=risk_before.level,
        riskLevel=risk_after.level,
        riskReasons=list(risk_after.reasons),
        goalImpacts=goal_impacts,
        recommendation=_recommendation(
            scenario,
            risk_after.level,
            max_delay,
            horizon_months=scenario.horizonMonths,
            balance_after=balance_after,
        ),
        horizonMonths=scenario.horizonMonths,
        atEventBefore=at_event_before,
        goalContributionsByEvent=as_float(contributed_by_event),
        fundedFromGoal=as_float(funded_from_goal),
        fundedFromBalance=as_float(funded_from_balance),
        eventRiskLevel=event_risk.level,
        minimumProjectedBalance=as_float(minimum_projected_balance),
    )
