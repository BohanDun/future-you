from app.models.customer import CustomerProfile
from app.models.scenario import ParsedScenario
from app.models.simulation import SimulationResult


def _primary_goal_impact(
    scenario: ParsedScenario,
    result: SimulationResult,
):
    target_impact = next(
        (
            impact
            for impact in result.goalImpacts
            if scenario.goalId and impact.goalId == scenario.goalId
        ),
        None,
    )
    if target_impact is None:
        target_impact = next(
            (
                impact
                for impact in result.goalImpacts
                if impact.monthsBefore != impact.monthsAfter
            ),
            (
                None
                if scenario.scenarioType == "extra_savings" and not scenario.goalId
                else result.goalImpacts[0] if result.goalImpacts else None
            ),
        )
    return target_impact


def _risk_tone(risk_level: str) -> str:
    if risk_level == "High":
        return (
            "I'd treat this as a stretch right now — the numbers show real pressure "
            "on your buffer and goals."
        )
    if risk_level == "Medium":
        return (
            "This looks manageable, but it's not completely free — you'll feel the "
            "trade-off in your goals or cash flow."
        )
    return "On paper this fits reasonably well with where you're at financially."


def _adjustment_hint(result: SimulationResult) -> str:
    recommendation = result.recommendation
    if not recommendation:
        return ""

    parts = [recommendation.description]
    if recommendation.weeklyAmount is not None:
        parts.append(
            f"One practical option: adjust by about "
            f"${recommendation.weeklyAmount:,.2f} per week."
        )
    return " ".join(parts)


def generate_mock_explanation(
    customer: CustomerProfile,
    scenario: ParsedScenario,
    result: SimulationResult,
    question: str | None = None,
) -> str:
    description = (scenario.description or "This change").lower()
    target_impact = _primary_goal_impact(scenario, result)
    tone = _risk_tone(result.riskLevel)

    if scenario.scenarioType == "one_off_purchase":
        if result.horizonMonths > 0 and result.atEventBefore is not None:
            impact = (
                f"By month {result.horizonMonths}, your projected available balance "
                f"before the {description} is ${result.atEventBefore.balance:,.2f}, "
                f"and ${result.after.balance:,.2f} would remain afterward."
            )
        else:
            impact = (
                f"A {description} would move your available balance from "
                f"${result.before.balance:,.2f} to ${result.after.balance:,.2f}."
            )
    elif scenario.scenarioType == "recurring_expense":
        impact = (
            f"The {description} would shift your monthly cash flow from "
            f"${result.before.monthlyCashFlow:,.2f} to "
            f"${result.after.monthlyCashFlow:,.2f}."
        )
    else:
        if target_impact:
            contribution = target_impact.monthlyContributionAfter
            impact = (
                f"The {description} would raise your {target_impact.goalName} "
                f"contribution to ${contribution:,.2f} per month."
            )
        else:
            impact = (
                f"The {description} would increase your monthly saving capacity "
                f"from ${result.before.monthlyCashFlow:,.2f} to "
                f"${result.after.monthlyCashFlow:,.2f}."
            )

    timeline = ""
    if (
        target_impact
        and target_impact.monthsBefore is not None
        and target_impact.monthsAfter is not None
    ):
        difference = target_impact.monthsAfter - target_impact.monthsBefore
        if difference > 0:
            timeline = (
                f" Your {target_impact.goalName} is delayed by {difference} "
                f"month{'s' if difference != 1 else ''}."
            )
        elif difference < 0:
            timeline = (
                f" Your {target_impact.goalName} moves forward by {abs(difference)} "
                f"month{'s' if difference != -1 else ''}."
            )
        else:
            timeline = f" Your {target_impact.goalName} timeline is unchanged."

    adjustment = _adjustment_hint(result)
    context = ""
    if question and question.strip():
        context = " Based on your question, here's how the numbers land."

    return (
        f"{context} {impact}{timeline} {tone} "
        f"The calculated risk level is {result.riskLevel}. {adjustment}"
    ).strip()


def unsupported_question_message() -> str:
    return (
        "I focus on money what-ifs — a purchase you're weighing, a bill or rent "
        "change, or saving a bit more toward a goal. Try something like "
        "\"Should I buy a $2,000 laptop?\" or "
        "\"What if I save an extra $50 per week?\""
    )


def missing_amount_message() -> str:
    return (
        "I couldn't pin down a dollar amount from that question. "
        "Add a price if you can — e.g. \"What happens if I buy a $2,000 laptop?\" — "
        "or name something common like a laptop or phone and I'll use a reasonable "
        "estimate for the demo."
    )


def generate_mock_coach_response(
    customer: CustomerProfile,
    question: str,
) -> str:
    normalized = question.strip().lower()
    goals = ", ".join(goal.name for goal in customer.goals[:3]) or "your goals"
    buffer_note = (
        f"You currently have ${customer.currentBalance:,.0f} available and save about "
        f"${customer.monthlySavings:,.0f} each month."
    )

    if any(word in normalized for word in ["stock", "stocks", "invest", "share", "etf"]):
        return (
            f"Happy to talk investing, {customer.name}. I won't pick individual stocks "
            f"for you, but a solid starting point is: build a small emergency buffer first, "
            f"then think about low-cost diversified funds matched to your time horizon and "
            f"risk comfort. {buffer_note} With {goals} on your radar, many people keep "
            f"short-term money in savings and only invest what they won't need for several years."
        )

    if any(
        phrase in normalized
        for phrase in [
            "bank account",
            "open an account",
            "open a account",
            "new account",
            "switch bank",
        ]
    ):
        return (
            f"Opening an account is usually straightforward, {customer.name}. You'll typically "
            f"need ID, proof of address, and sometimes a minimum opening deposit — online "
            f"applications take minutes, while branch visits help if you want someone to walk "
            f"you through products. {buffer_note} If you're mainly saving toward {goals}, ask "
            f"what account types fit those timelines before you sign up."
        )

    if any(word in normalized for word in ["budget", "spending", "save more", "cut back"]):
        return (
            f"Let's keep it practical, {customer.name}. {buffer_note} A simple next step is "
            f"to pick one category to trim for a month and redirect that cash toward "
            f"{goals}. Small, steady changes beat dramatic cuts you can't sustain."
        )

    return (
        f"Good question, {customer.name}. {buffer_note} I'm here to talk through purchases, "
        f"saving, bills, investing basics, or how bank products work — and when you want "
        f"hard numbers on a \"what if\", ask with a dollar amount and I'll model it against "
        f"{goals}."
    )
