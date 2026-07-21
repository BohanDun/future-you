import re

from app.models.scenario import ParsedScenario

_AMOUNT_PATTERN = re.compile(
    r"\$?\s*([0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?)"
)


def _extract_amount(question: str) -> float | None:
    for match in _AMOUNT_PATTERN.finditer(question):
        suffix = question[match.end():]
        if re.match(r"\s*(?:months?|years?)\b", suffix):
            continue
        return float(match.group(1).replace(",", ""))
    return None


def _is_general_coach_question(question: str) -> bool:
    coach_topics = [
        "stock",
        "stocks",
        "invest",
        "investing",
        "share",
        "shares",
        "etf",
        "crypto",
        "bank account",
        "open an account",
        "open a account",
        "new account",
        "switch bank",
        "credit score",
        "mortgage broker",
        "tax return",
        "superannuation",
        "retirement fund",
        "financial advice",
        "budget tip",
        "how do i save",
        "how can i save",
    ]
    return any(topic in question for topic in coach_topics)


def parse_question_mock(question: str) -> ParsedScenario:
    normalized = question.strip().lower()
    amount = _extract_amount(normalized)
    horizon_months, timing_label = extract_horizon(normalized)

    if _is_general_coach_question(normalized):
        return ParsedScenario(
            scenarioType="unknown",
            amount=None,
            frequency=None,
            description=None,
            goalId=None,
            horizonMonths=horizon_months,
            timingLabel=timing_label,
        )

    if any(
        keyword in normalized
        for keyword in [
            "buy",
            "purchase",
            "pay for",
            "book",
            "afford",
            "get a",
            "get the",
            "need a",
            "spend on",
            "thinking about",
            "should i buy",
            "should i get",
            "splurge",
            "treat myself",
            "cost of",
        ]
    ):
        return ParsedScenario(
            scenarioType="one_off_purchase",
            amount=amount,
            frequency="one_time",
            description=_extract_purchase_description(normalized),
            goalId=_extract_goal_id(normalized),
            horizonMonths=horizon_months,
            timingLabel=timing_label,
        )

    if any(
        keyword in normalized
        for keyword in [
            "rent increases",
            "rent increase",
            "costs more",
            "pay more",
            "bills",
            "subscription",
            "utilities",
            "insurance",
            "groceries",
            "costs go up",
        ]
    ):
        return ParsedScenario(
            scenarioType="recurring_expense",
            amount=amount,
            frequency=_extract_frequency(normalized),
            description="Recurring expense increase",
            goalId=None,
            horizonMonths=horizon_months,
            timingLabel=timing_label,
        )

    if any(
        keyword in normalized
        for keyword in [
            "save an extra",
            "extra savings",
            "save another",
            "put away",
            "put aside",
            "save more",
            "start saving",
        ]
    ):
        return ParsedScenario(
            scenarioType="extra_savings",
            amount=amount,
            frequency=_extract_frequency(normalized),
            description="Extra savings",
            goalId=_extract_goal_id(normalized),
            horizonMonths=horizon_months,
            timingLabel=timing_label,
        )

    return ParsedScenario(
        scenarioType="unknown",
        amount=None,
        frequency=None,
        description=None,
        goalId=None,
        horizonMonths=horizon_months,
        timingLabel=timing_label,
    )


_DURATION_WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
}
_DURATION_VALUE = rf"(?:\d+|{'|'.join(_DURATION_WORDS)})"


def _duration_value(value: str) -> int:
    return int(value) if value.isdigit() else _DURATION_WORDS[value]


def extract_horizon(question: str) -> tuple[int, str | None]:
    if re.search(r"\bnext\s+month\b", question):
        return 1, "next month"
    if re.search(r"\bnext\s+year\b", question):
        return 12, "next year"
    duration_patterns = (
        rf"\b(?:in|after)\s+(?P<value>{_DURATION_VALUE})\s+"
        r"(?P<unit>months?|years?)\b",
        rf"\b(?P<value>{_DURATION_VALUE})\s+(?P<unit>months?|years?)\s+"
        r"(?:later|from\s+now|away)\b",
    )
    for pattern in duration_patterns:
        match = re.search(pattern, question)
        if match:
            value = _duration_value(match.group("value"))
            months = value * 12 if match.group("unit").startswith("year") else value
            return months, match.group(0)
    match = re.search(
        r"\b(?:in\s+)?(?:a|one)\s+year(?:\s+(?:later|from\s+now|away))?\b",
        question,
    )
    if match:
        return 12, match.group(0)
    return 0, None


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
