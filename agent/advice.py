"""Semantic routing for Advice mode."""

import json
import logging
import re

from agent.bedrock_client import invoke_bedrock
from agent.config import get_ai_mode
from agent.enrichment import enrich_scenario
from agent.json_utils import parse_json_object
from agent.scenario_parser import parse_question_mock
from agent.schemas import AdviceRoute
from app.models.agent_action import ConversationMessage
from app.models.customer import CustomerProfile
from app.models.scenario import ParsedScenario

logger = logging.getLogger(__name__)

OFF_TOPIC_RESPONSE = (
    "I’m focused on financial planning and money questions. You can ask me about "
    "budgeting, saving, goals, spending, or a financial what-if scenario."
)
SAFETY_SUPPORT_RESPONSE = (
    "I’m really sorry you’re dealing with this. Your immediate safety matters more "
    "than financial planning right now—please contact local emergency services if "
    "you may act on these thoughts, and reach out to someone you trust who can stay "
    "with you."
)

_SAFETY_PATTERN = re.compile(
    r"\b(suicid(?:e|al)|self[- ]?harm|hurt myself|kill myself|end my life|"
    r"don'?t want to live|want to die)\b",
    re.IGNORECASE,
)
_MOCK_FINANCIAL_PATTERN = re.compile(
    r"\b(money|financial|finance|budget|sav(?:e|ing|ings)|income|salary|expense|"
    r"spending|balance|bank|account|credit|loan|debt|mortgage|invest\w*|stocks?|"
    r"shares?|funds?|crypto|tax|"
    r"insurance|retirement|afford|cost|price|rent|bill|goal)\b|[$€£¥]\s*\d",
    re.IGNORECASE,
)
_SCENARIO_FOLLOW_UP = re.compile(
    r"\b(what about|how about|instead|then|next month|next year|"
    r"(?:in|after)\s+(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten|"
    r"eleven|twelve)\s+(?:months?|years?)|"
    r"(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)"
    r"\s+(?:months?|years?)\s+(?:later|from\s+now|away))\b",
    re.IGNORECASE,
)


def _router_system(profile: CustomerProfile) -> str:
    goals = [
        {"id": goal.goalId, "name": goal.name}
        for goal in profile.goals
    ]
    return f"""You route messages for the Advice mode of a financial wellbeing app.
Return one JSON object only. Do not answer the customer.

Allowed kinds:
- simulation: a financial what-if with a cost, income/expense change, or savings change
- financial_advice: a general money or financial education question
- off_topic: unrelated to personal finance
- safety_support: credible self-harm or suicide language

For simulation include a scenario with scenarioType, amount, frequency, description,
goalId, horizonMonths, and timingLabel. Supported scenarioType values are
one_off_purchase, recurring_expense, and extra_savings. frequency is weekly, monthly,
yearly, one_time, or null. Use only
a goal ID from this trusted list when the customer clearly identifies that goal:
{json.dumps(goals)}
Otherwise set goalId to null. Do not invent a goal ID. Preserve the amount stated by
the customer. If a common scenario omits an amount, amount may be null so the
application can add an explicitly labelled estimate.

Set horizonMonths to 0 for an immediate event, 1 for next month, 12 for next year,
or the explicitly requested number of months. timingLabel preserves the customer's
short timing phrase, or null when no future timing is stated.

For every non-simulation kind, set scenario to null.
Understand natural phrasing and languages; do not route by a fixed keyword list."""


def _question_with_context(
    question: str,
    history: list[ConversationMessage],
) -> str:
    if not _SCENARIO_FOLLOW_UP.search(question):
        return question
    previous_user_message = next(
        (
            item.content
            for item in reversed(history)
            if item.role == "user"
            and parse_question_mock(item.content).scenarioType != "unknown"
        ),
        None,
    )
    return f"{previous_user_message}\nFollow-up: {question}" if previous_user_message else question


def _merge_follow_up_details(
    question: str,
    scenario: ParsedScenario,
) -> ParsedScenario:
    """Apply explicit values from a short follow-up to its inherited scenario."""
    if not _SCENARIO_FOLLOW_UP.search(question):
        return scenario
    follow_up = parse_question_mock(question)
    updates: dict[str, object] = {}
    if follow_up.amount is not None:
        updates["amount"] = follow_up.amount
    if follow_up.horizonMonths > 0:
        updates["horizonMonths"] = follow_up.horizonMonths
        updates["timingLabel"] = follow_up.timingLabel
    if follow_up.frequency is not None:
        updates["frequency"] = follow_up.frequency
    return scenario.model_copy(update=updates) if updates else scenario


def _mock_route(
    profile: CustomerProfile,
    question: str,
    history: list[ConversationMessage],
) -> AdviceRoute:
    if _SAFETY_PATTERN.search(question):
        return AdviceRoute(kind="safety_support")
    contextual_question = _question_with_context(question, history)
    scenario = _merge_follow_up_details(
        question,
        parse_question_mock(contextual_question),
    )
    scenario = enrich_scenario(question, scenario)
    if scenario.scenarioType != "unknown":
        normalized = contextual_question.casefold()
        named_goal = next(
            (
                goal
                for goal in profile.goals
                if goal.name.casefold() in normalized or goal.goalId.casefold() in normalized
            ),
            None,
        )
        if named_goal is not None:
            scenario = scenario.model_copy(update={"goalId": named_goal.goalId})
        elif scenario.goalId and not any(
            goal.goalId == scenario.goalId for goal in profile.goals
        ):
            scenario = scenario.model_copy(update={"goalId": None})
        return AdviceRoute(kind="simulation", scenario=scenario)
    if _MOCK_FINANCIAL_PATTERN.search(question):
        return AdviceRoute(kind="financial_advice")
    return AdviceRoute(kind="off_topic")


def _inherited_follow_up_route(
    profile: CustomerProfile,
    question: str,
    history: list[ConversationMessage],
) -> AdviceRoute | None:
    if not history or not _SCENARIO_FOLLOW_UP.search(question):
        return None
    inherited = _mock_route(profile, question, history)
    return inherited if inherited.kind == "simulation" else None


def _ground_follow_up_route(
    route: AdviceRoute,
    inherited: AdviceRoute | None,
    question: str,
) -> AdviceRoute:
    if inherited is None or inherited.scenario is None:
        return route
    if route.kind != "simulation" or route.scenario is None:
        return inherited

    current = parse_question_mock(question)
    updates: dict[str, object] = {}
    if not route.scenario.description:
        updates.update({
            "scenarioType": inherited.scenario.scenarioType,
            "description": inherited.scenario.description,
            "frequency": inherited.scenario.frequency,
            "goalId": inherited.scenario.goalId,
        })
    same_subject = (
        not route.scenario.description
        or route.scenario.description.casefold()
        == (inherited.scenario.description or "").casefold()
    )
    if current.amount is None and same_subject:
        updates["amount"] = inherited.scenario.amount
    grounded = route.scenario.model_copy(update=updates)
    grounded = _merge_follow_up_details(question, grounded)
    return route.model_copy(update={"scenario": grounded})


def route_advice_question(
    profile: CustomerProfile,
    question: str,
    history: list[ConversationMessage] | None = None,
) -> AdviceRoute:
    recent_history = (history or [])[-12:]
    if _SAFETY_PATTERN.search(question):
        return AdviceRoute(kind="safety_support")
    if get_ai_mode() != "bedrock":
        return _mock_route(profile, question, recent_history)
    inherited_route = _inherited_follow_up_route(profile, question, recent_history)
    try:
        transcript = "\n".join(
            f"{item.role.title()}: {item.content}"
            for item in recent_history
        )
        response = invoke_bedrock(
            system_prompt=_router_system(profile),
            user_prompt=(
                f"Recent conversation:\n{transcript or 'None'}\n\n"
                f"Current message:\n{question.strip()}\n\n"
                "Resolve short follow-ups from the recent conversation. For example, "
                "'What about next month?' keeps the previous scenario and only changes timing."
            ),
            max_tokens=300,
            temperature=0,
        )
        route = AdviceRoute.model_validate(parse_json_object(response))
        route = _ground_follow_up_route(route, inherited_route, question)
        if route.scenario is not None:
            valid_goal_ids = {goal.goalId for goal in profile.goals}
            if route.scenario.goalId not in valid_goal_ids:
                route = route.model_copy(update={
                    "scenario": route.scenario.model_copy(update={"goalId": None})
                })
            route = route.model_copy(update={
                "scenario": enrich_scenario(
                    question,
                    _merge_follow_up_details(question, route.scenario),
                )
            })
        return route
    except Exception:
        logger.warning("Advice routing failed; using deterministic fallback", exc_info=True)
        return inherited_route or _mock_route(profile, question, recent_history)
