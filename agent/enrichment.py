"""Fill in missing scenario details using sensible demo defaults."""

from agent.scenario_parser import extract_horizon
from app.models.scenario import ParsedScenario

_PURCHASE_DEFAULTS: dict[str, float] = {
    "laptop": 2000,
    "phone": 1200,
    "car": 15000,
    "holiday": 3500,
    "trip": 3500,
    "japan trip": 3000,
    "university fees": 8000,
    "course fees": 8000,
    "wedding": 8000,
    "moving costs": 2500,
    "one-time purchase": 1000,
}

_RECURRING_DEFAULTS: dict[str, tuple[float, str]] = {
    "rent": (50, "weekly"),
    "rent increase": (50, "weekly"),
    "recurring expense increase": (50, "weekly"),
    "subscription": (15, "monthly"),
    "bills": (30, "monthly"),
    "insurance": (40, "monthly"),
}

_SAVINGS_DEFAULTS: tuple[float, str] = (50, "weekly")


def _normalize(text: str | None) -> str:
    return (text or "").strip().lower()


def _match_purchase_default(description: str | None, question: str) -> float | None:
    combined = f"{_normalize(description)} {_normalize(question)}"
    question_only = _normalize(question)
    for label, amount in sorted(_PURCHASE_DEFAULTS.items(), key=lambda item: -len(item[0])):
        if label not in combined:
            continue
        if label == "one-time purchase" and label not in question_only:
            continue
        return amount
    return None


def _estimated_label(description: str | None, amount: float) -> str:
    base = (description or "Purchase").split(" (estimated")[0].strip()
    if not base:
        base = "Purchase"
    return f"{base} (estimated ${amount:,.0f})"


def enrich_scenario(question: str, scenario: ParsedScenario) -> ParsedScenario:
    if scenario.horizonMonths == 0:
        horizon_months, timing_label = extract_horizon(_normalize(question))
        if horizon_months:
            scenario = scenario.model_copy(update={
                "horizonMonths": horizon_months,
                "timingLabel": scenario.timingLabel or timing_label,
            })
    if scenario.amount is not None:
        return scenario

    if scenario.scenarioType == "one_off_purchase":
        inferred = _match_purchase_default(scenario.description, question)
        if inferred is None:
            return scenario
        return scenario.model_copy(
            update={
                "amount": inferred,
                "frequency": scenario.frequency or "one_time",
                "description": _estimated_label(scenario.description, inferred),
            }
        )

    if scenario.scenarioType == "recurring_expense":
        label = _normalize(scenario.description)
        for key, (amount, frequency) in _RECURRING_DEFAULTS.items():
            if key in label or key in _normalize(question):
                return scenario.model_copy(
                    update={
                        "amount": amount,
                        "frequency": scenario.frequency or frequency,
                        "description": _estimated_label(
                            scenario.description or "Recurring expense increase",
                            amount,
                        ),
                    }
                )

    if scenario.scenarioType == "extra_savings":
        amount, frequency = _SAVINGS_DEFAULTS
        if "extra savings" in _normalize(scenario.description) or "save" in _normalize(question):
            return scenario.model_copy(
                update={
                    "amount": amount,
                    "frequency": scenario.frequency or frequency,
                    "description": scenario.description or "Extra savings",
                }
            )

    return scenario


def uses_estimated_amount(scenario: ParsedScenario) -> bool:
    return bool(scenario.description and "(estimated $" in scenario.description)
