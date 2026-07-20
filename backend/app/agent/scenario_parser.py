import re

from app.models.scenario import ParsedScenario

_AMOUNT_PATTERN = re.compile(
    r"\$?\s*([0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?)"
)


def _extract_amount(question: str) -> float | None:
    match = _AMOUNT_PATTERN.search(question)

    if match is None:
        return None

    return float(match.group(1).replace(",", ""))


def parse_question_mock(question: str) -> ParsedScenario:
    normalized = question.strip().lower()
    amount = _extract_amount(normalized)

    if any(
        keyword in normalized
        for keyword in ["buy", "purchase", "pay for", "book", "afford"]
    ):
        return ParsedScenario(
            scenarioType="one_off_purchase",
            amount=amount,
            frequency="one_time",
            description=_extract_purchase_description(normalized),
            goalId=_extract_goal_id(normalized),
        )

    if any(
        keyword in normalized
        for keyword in ["rent increases", "rent increase", "costs more"]
    ):
        return ParsedScenario(
            scenarioType="recurring_expense",
            amount=amount,
            frequency=_extract_frequency(normalized),
            description="Recurring expense increase",
            goalId=None,
        )

    if any(
        keyword in normalized
        for keyword in ["save an extra", "extra savings", "save another"]
    ):
        return ParsedScenario(
            scenarioType="extra_savings",
            amount=amount,
            frequency=_extract_frequency(normalized),
            description="Extra savings",
            goalId=_extract_goal_id(normalized),
        )

    return ParsedScenario(
        scenarioType="unknown",
        amount=None,
        frequency=None,
        description=None,
        goalId=None,
    )


def _extract_frequency(question: str) -> str | None:
    if "per week" in question or "weekly" in question:
        return "weekly"

    if "per month" in question or "monthly" in question:
        return "monthly"

    if "per year" in question or "yearly" in question:
        return "yearly"

    return None


def _extract_purchase_description(question: str) -> str:
    if "japan" in question and any(word in question for word in ["trip", "holiday"]):
        return "Japan trip"

    known_items = [
        "laptop",
        "car",
        "holiday",
        "trip",
        "phone",
        "university fees",
    ]

    for item in known_items:
        if item in question:
            return item.title()

    return "One-time purchase"


def _extract_goal_id(question: str) -> str | None:
    aliases = {
        "house_deposit": ["house", "home", "deposit"],
        "japan_holiday": ["japan", "holiday", "trip"],
        "emergency_fund": ["emergency"],
    }
    for goal_id, keywords in aliases.items():
        if any(keyword in question for keyword in keywords):
            return goal_id
    return None
