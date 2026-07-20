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
        for keyword in ["buy", "purchase", "pay for", "book"]
    ):
        return ParsedScenario(
            scenarioType="one_off_purchase",
            amount=amount,
            frequency="one_time",
            description=_extract_purchase_description(normalized),
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
        )

    return ParsedScenario(
        scenarioType="unknown",
        amount=None,
        frequency=None,
        description=None,
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