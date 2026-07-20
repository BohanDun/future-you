"""Deterministic planning tools for interactive financial decisions."""

from decimal import ROUND_CEILING, Decimal

from app.financial import assess_financial_risk, calculate_goal_completion_months
from app.financial.money import as_decimal, as_float, money
from app.financial.risk import RiskAssessment
from app.models.customer import CustomerProfile, FinancialGoal
from app.models.planning import (
    AffordabilitySummary,
    GoalAllocation,
    GoalAllocationResult,
    StressGoalImpact,
    StressTestResult,
)
from app.models.scenario import ParsedScenario
from app.services.simulation_service import run_simulation

RISK_RANK = {"Low": 0, "Medium": 1, "High": 2}


def _goal(customer: CustomerProfile, goal_id: str) -> FinancialGoal:
    selected = next((goal for goal in customer.goals if goal.goalId == goal_id), None)
    if selected is None:
        raise ValueError(f"Unknown financial goal: {goal_id}")
    return selected


def _purchase_risk(customer: CustomerProfile, goal_id: str, amount: Decimal):
    if amount <= 0:
        return assess_financial_risk(
            monthly_cash_flow_before=customer.monthlySavings,
            monthly_cash_flow_after=customer.monthlySavings,
            available_balance_after=customer.currentBalance,
            monthly_expenses=customer.monthlyExpenses,
            max_goal_delay_months=0,
        )

    result = run_simulation(
        customer,
        ParsedScenario(
            scenarioType="one_off_purchase",
            amount=as_float(amount),
            frequency="one_time",
            description="Interactive purchase",
            goalId=goal_id,
        ),
    )
    return RiskAssessment(
        level=result.riskLevel,
        reasons=tuple(result.riskReasons),
    )


def _max_purchase_for_risk(
    customer: CustomerProfile,
    goal_id: str,
    maximum_risk: str,
) -> int:
    low_cents = 0
    high_cents = int(money(customer.currentBalance) * 100)
    best_cents = 0
    allowed_rank = RISK_RANK[maximum_risk]

    while low_cents <= high_cents:
        midpoint = (low_cents + high_cents) // 2
        amount = Decimal(midpoint) / Decimal("100")
        assessment = _purchase_risk(customer, goal_id, amount)
        if RISK_RANK[assessment.level] <= allowed_rank:
            best_cents = midpoint
            low_cents = midpoint + 1
        else:
            high_cents = midpoint - 1

    return best_cents


def _boundary_reasons(
    customer: CustomerProfile,
    goal_id: str,
    limit_cents: int,
) -> list[str]:
    maximum_cents = int(money(customer.currentBalance) * 100)
    next_cents = limit_cents + 1
    if next_cents > maximum_cents:
        return []
    assessment = _purchase_risk(
        customer,
        goal_id,
        Decimal(next_cents) / Decimal("100"),
    )
    return list(assessment.reasons)


def calculate_affordability(
    customer: CustomerProfile,
    goal_id: str,
) -> AffordabilitySummary:
    target = _goal(customer, goal_id)
    low_limit_cents = _max_purchase_for_risk(customer, goal_id, "Low")
    medium_limit_cents = _max_purchase_for_risk(customer, goal_id, "Medium")
    maximum_cents = int(money(customer.currentBalance) * 100)
    high_starts = (
        Decimal(medium_limit_cents + 1) / Decimal("100")
        if medium_limit_cents < maximum_cents
        else None
    )
    expenses = as_decimal(customer.monthlyExpenses)
    reserve_months = (
        as_decimal(customer.currentBalance) / expenses
        if expenses > 0
        else Decimal("0")
    )

    return AffordabilitySummary(
        customerId=customer.customerId,
        goalId=target.goalId,
        goalName=target.name,
        availableBalance=as_float(customer.currentBalance),
        reserveMonths=as_float(reserve_months.quantize(Decimal("0.01"))),
        lowRiskLimit=as_float(Decimal(low_limit_cents) / Decimal("100")),
        mediumRiskLimit=as_float(Decimal(medium_limit_cents) / Decimal("100")),
        highRiskStartsAt=as_float(high_starts) if high_starts is not None else None,
        lowRiskBoundaryReasons=_boundary_reasons(
            customer,
            goal_id,
            low_limit_cents,
        ),
        mediumRiskBoundaryReasons=_boundary_reasons(
            customer,
            goal_id,
            medium_limit_cents,
        ),
    )


def run_stress_test(
    customer: CustomerProfile,
    *,
    income_loss_months: int,
    unexpected_expense: float,
) -> StressTestResult:
    expenses = as_decimal(customer.monthlyExpenses)
    balance_before = as_decimal(customer.currentBalance)
    shock_cost = expenses * income_loss_months + as_decimal(unexpected_expense)
    balance_after = money(balance_before - shock_cost)
    cash_flow_during_shock = -expenses if income_loss_months else as_decimal(
        customer.monthlySavings
    )
    runway_before = balance_before / expenses if expenses > 0 else Decimal("0")
    runway_after = max(balance_after, Decimal("0")) / expenses if expenses > 0 else Decimal("0")

    risk = assess_financial_risk(
        monthly_cash_flow_before=customer.monthlySavings,
        monthly_cash_flow_after=cash_flow_during_shock,
        available_balance_after=balance_after,
        monthly_expenses=customer.monthlyExpenses,
        max_goal_delay_months=income_loss_months,
    )
    impacts: list[StressGoalImpact] = []
    for goal in customer.goals:
        before = calculate_goal_completion_months(
            goal.target,
            goal.current,
            goal.monthlyContribution,
        )
        after = before + income_loss_months if before is not None else None
        impacts.append(
            StressGoalImpact(
                goalId=goal.goalId,
                goalName=goal.name,
                monthsBefore=before,
                monthsAfter=after,
            )
        )

    recommendation = (
        "Protect essential expenses and pause discretionary goal contributions during the shock."
        if risk.level == "High"
        else "Rebuild the emergency buffer before increasing discretionary spending."
    )
    return StressTestResult(
        customerId=customer.customerId,
        balanceBefore=as_float(balance_before),
        balanceAfter=as_float(balance_after),
        runwayMonthsBefore=as_float(runway_before.quantize(Decimal("0.01"))),
        runwayMonthsAfter=as_float(runway_after.quantize(Decimal("0.01"))),
        monthlyCashFlowDuringShock=as_float(cash_flow_during_shock),
        riskLevel=risk.level,
        riskReasons=list(risk.reasons),
        goalImpacts=impacts,
        recommendation=recommendation,
    )


def optimize_goal_allocation(
    customer: CustomerProfile,
    *,
    priority_goal_id: str,
    target_months: int,
) -> GoalAllocationResult:
    priority = _goal(customer, priority_goal_id)
    available = as_decimal(customer.monthlySavings)
    remaining = max(
        as_decimal(priority.target) - as_decimal(priority.current),
        Decimal("0"),
    )
    earliest = calculate_goal_completion_months(
        priority.target,
        priority.current,
        available,
    )
    required = (
        (remaining / Decimal(target_months)).quantize(
            Decimal("0.01"),
            rounding=ROUND_CEILING,
        )
        if remaining > 0
        else Decimal("0")
    )
    feasible = required <= available
    priority_allocation = min(required, available)
    remaining_budget = max(available - priority_allocation, Decimal("0"))
    other_goals = [goal for goal in customer.goals if goal.goalId != priority_goal_id]
    other_total = sum(
        (as_decimal(goal.monthlyContribution) for goal in other_goals),
        Decimal("0"),
    )
    allocation_values: dict[str, Decimal] = {priority_goal_id: priority_allocation}

    allocated = Decimal("0")
    for index, goal in enumerate(other_goals):
        if index == len(other_goals) - 1:
            value = money(remaining_budget - allocated)
        elif other_total > 0:
            value = money(
                remaining_budget
                * as_decimal(goal.monthlyContribution)
                / other_total
            )
            allocated += value
        else:
            value = Decimal("0")
        allocation_values[goal.goalId] = value

    allocations: list[GoalAllocation] = []
    for goal in customer.goals:
        contribution_after = allocation_values.get(goal.goalId, Decimal("0"))
        allocations.append(
            GoalAllocation(
                goalId=goal.goalId,
                goalName=goal.name,
                monthlyContributionBefore=as_float(goal.monthlyContribution),
                monthlyContributionAfter=as_float(contribution_after),
                monthsBefore=calculate_goal_completion_months(
                    goal.target,
                    goal.current,
                    goal.monthlyContribution,
                ),
                monthsAfter=calculate_goal_completion_months(
                    goal.target,
                    goal.current,
                    contribution_after,
                ),
            )
        )

    if feasible:
        summary = (
            f"Allocate ${as_float(priority_allocation):,.2f} per month to "
            f"{priority.name} and distribute the remaining "
            f"${as_float(remaining_budget):,.2f} across other goals."
        )
    else:
        summary = (
            f"The requested deadline is not feasible. The earliest possible "
            f"timeline is {earliest} months using all available monthly savings."
        )

    return GoalAllocationResult(
        customerId=customer.customerId,
        priorityGoalId=priority_goal_id,
        requestedMonths=target_months,
        earliestPossibleMonths=earliest,
        feasible=feasible,
        monthlySavingsAvailable=as_float(available),
        allocations=allocations,
        summary=summary,
    )
