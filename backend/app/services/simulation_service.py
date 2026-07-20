import math

from app.models.customer import CustomerProfile
from app.models.scenario import ParsedScenario
from app.models.simulation import (
    FinancialSnapshot,
    Recommendation,
    SimulationResult,
)


def _house_goal_months(
    customer: CustomerProfile,
    current_amount: float,
) -> int | None:
    house_goal = next(
        (
            goal
            for goal in customer.goals
            if goal.goalId == "house_deposit"
        ),
        None,
    )

    if house_goal is None:
        return None

    remaining = max(house_goal.target - current_amount, 0)

    if house_goal.monthlyContribution <= 0:
        return None

    return math.ceil(
        remaining / house_goal.monthlyContribution
    )


def run_simulation(
    customer: CustomerProfile,
    scenario: ParsedScenario,
) -> SimulationResult:
    before_goal_months = _house_goal_months(
        customer,
        customer.currentBalance,
    )

    before = FinancialSnapshot(
        balance=customer.currentBalance,
        monthlyCashFlow=customer.monthlySavings,
        goalMonths=before_goal_months,
    )

    if scenario.scenarioType == "one_off_purchase":
        return _simulate_one_off_purchase(
            customer,
            scenario,
            before,
        )

    if scenario.scenarioType == "recurring_expense":
        return _simulate_recurring_expense(
            customer,
            scenario,
            before,
        )

    if scenario.scenarioType == "extra_savings":
        return _simulate_extra_savings(
            customer,
            scenario,
            before,
        )

    raise ValueError("Unsupported scenario")


def _simulate_one_off_purchase(
    customer: CustomerProfile,
    scenario: ParsedScenario,
    before: FinancialSnapshot,
) -> SimulationResult:
    amount = scenario.amount or 0
    new_balance = customer.currentBalance - amount

    after = FinancialSnapshot(
        balance=new_balance,
        monthlyCashFlow=customer.monthlySavings,
        goalMonths=_house_goal_months(
            customer,
            new_balance,
        ),
    )

    risk = "Low"

    if new_balance < 0:
        risk = "High"
    elif new_balance < 5000:
        risk = "Medium"

    return SimulationResult(
        before=before,
        after=after,
        riskLevel=risk,
        recommendation=Recommendation(
            description="Reduce discretionary spending temporarily",
            weeklyAmount=40,
        ),
    )


def _simulate_recurring_expense(
    customer: CustomerProfile,
    scenario: ParsedScenario,
    before: FinancialSnapshot,
) -> SimulationResult:
    amount = scenario.amount or 0

    if scenario.frequency == "weekly":
        monthly_extra_cost = amount * 52 / 12
    elif scenario.frequency == "yearly":
        monthly_extra_cost = amount / 12
    else:
        monthly_extra_cost = amount

    new_cash_flow = (
        customer.monthlySavings - monthly_extra_cost
    )

    after = FinancialSnapshot(
        balance=customer.currentBalance,
        monthlyCashFlow=new_cash_flow,
        goalMonths=before.goalMonths,
    )

    risk = "Low"

    if new_cash_flow < 0:
        risk = "High"
    elif new_cash_flow < customer.monthlySavings * 0.5:
        risk = "Medium"

    return SimulationResult(
        before=before,
        after=after,
        riskLevel=risk,
        recommendation=Recommendation(
            description="Review recurring expenses",
            weeklyAmount=None,
        ),
    )


def _simulate_extra_savings(
    customer: CustomerProfile,
    scenario: ParsedScenario,
    before: FinancialSnapshot,
) -> SimulationResult:
    amount = scenario.amount or 0

    if scenario.frequency == "weekly":
        extra_monthly = amount * 52 / 12
    elif scenario.frequency == "yearly":
        extra_monthly = amount / 12
    else:
        extra_monthly = amount

    after = FinancialSnapshot(
        balance=customer.currentBalance,
        monthlyCashFlow=customer.monthlySavings + extra_monthly,
        goalMonths=before.goalMonths,
    )

    return SimulationResult(
        before=before,
        after=after,
        riskLevel="Low",
        recommendation=Recommendation(
            description="Continue the additional savings plan",
            weeklyAmount=(
                amount
                if scenario.frequency == "weekly"
                else None
            ),
        ),
    )
