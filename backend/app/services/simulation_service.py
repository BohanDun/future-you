"""Adapt validated API models to the deterministic Person 2 financial tools."""

import math
from decimal import ROUND_CEILING, Decimal

from app.financial import (
    apply_extra_savings,
    apply_one_time_purchase,
    apply_recurring_expense,
    assess_financial_risk,
    calculate_goal_completion_months,
    calculate_monthly_cash_flow,
)
from app.financial.money import as_decimal, as_float, money
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
) -> FinancialGoal | None:
    if scenario.goalId:
        selected = next(
            (goal for goal in customer.goals if goal.goalId == scenario.goalId),
            None,
        )
        if selected:
            return selected

    description = (scenario.description or "").lower()
    aliases = {
        "house_deposit": ("house", "home", "deposit"),
        "japan_holiday": ("japan", "holiday", "trip"),
        "emergency_fund": ("emergency",),
    }
    for goal_id, keywords in aliases.items():
        if any(keyword in description for keyword in keywords):
            selected = next(
                (goal for goal in customer.goals if goal.goalId == goal_id),
                None,
            )
            if selected:
                return selected

    return next(
        (goal for goal in customer.goals if goal.goalId == "house_deposit"),
        customer.goals[0] if customer.goals else None,
    )


def _goal_impacts(
    customer: CustomerProfile,
    scenario: ParsedScenario,
    monthly_delta: Decimal,
) -> list[GoalImpact]:
    total_contributions = sum(
        (as_decimal(goal.monthlyContribution) for goal in customer.goals),
        Decimal("0"),
    )
    primary = _target_goal(customer, scenario)
    impacts: list[GoalImpact] = []

    for goal in customer.goals:
        current_after = as_decimal(goal.current)
        contribution_after = as_decimal(goal.monthlyContribution)

        if scenario.scenarioType == "one_off_purchase" and goal is primary:
            current_after = max(
                current_after - as_decimal(scenario.amount or 0),
                Decimal("0"),
            )
        elif scenario.scenarioType == "recurring_expense":
            available_for_goals = max(
                total_contributions + monthly_delta,
                Decimal("0"),
            )
            scale = (
                available_for_goals / total_contributions
                if total_contributions > 0
                else Decimal("0")
            )
            contribution_after *= scale
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
        impacts.append(
            GoalImpact(
                goalId=goal.goalId,
                goalName=goal.name,
                monthsBefore=months_before,
                monthsAfter=months_after,
                monthlyContributionBefore=as_float(goal.monthlyContribution),
                monthlyContributionAfter=as_float(contribution_after),
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
) -> Recommendation:
    amount = scenario.amount or 0
    if scenario.scenarioType == "one_off_purchase":
        if risk_level == "Low" and max_goal_delay == 0:
            return Recommendation(description="This purchase fits within the current plan.")
        weekly_recovery = None
        if amount > 0:
            units = (
                as_decimal(amount) / Decimal("52") / Decimal("5")
            ).to_integral_value(rounding=ROUND_CEILING)
            weekly_recovery = as_float(units * Decimal("5"))
        return Recommendation(
            description="Reduce discretionary spending temporarily to recover the goal delay.",
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
    cash_flow_after = cash_flow_before
    monthly_delta = Decimal("0")

    if scenario.scenarioType == "one_off_purchase":
        balance_after = apply_one_time_purchase(
            customer.currentBalance,
            scenario.amount,
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
    else:
        raise ValueError("Unsupported scenario")

    goal_impacts = _goal_impacts(customer, scenario, monthly_delta)
    primary = _target_goal(customer, scenario)
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
    return SimulationResult(
        before=before,
        after=after,
        beforeRiskLevel=risk_before.level,
        riskLevel=risk_after.level,
        riskReasons=list(risk_after.reasons),
        goalImpacts=goal_impacts,
        recommendation=_recommendation(scenario, risk_after.level, max_delay),
    )
