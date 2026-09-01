import re
from dataclasses import dataclass, field

from app.models.agent_action import (
    AgentOperation,
    CreateGoalOperation,
    SetGoalOperation,
    SetProfileOperation,
)
from app.models.customer import CustomerProfile

INTERNAL_REQUEST_MESSAGE = (
    "I can’t share internal prompts, configuration, tools, or credentials. "
    "I’m still happy to help you update your financial profile or goals."
)
UNSUPPORTED_OPERATION_MESSAGE = (
    "I can help you plan goals and update the figures shown in Future You, but I "
    "can’t make transfers, payments, purchases, investments, or deletions."
)
MISMATCH_MESSAGE = (
    "I want to make sure I understood you correctly, so I haven’t prepared that "
    "change. Please tell me which profile figure or goal you want to update."
)


_INTERNAL_PATTERNS = (
    r"\b(system|developer|hidden|internal)\s+(prompt|instruction|message)s?\b",
    r"\b(reveal|show|print|return|repeat|ignore)\b.{0,45}\b(prompt|instruction)s?\b",
    r"\b(api|access|secret|session|bearer)\s*[-_ ]?(key|token)s?\b",
    r"\b(credentials?|environment variables?|configuration)\b",
    r"\b(chain of thought|reasoning trace|tool (?:list|schema|definition)s?)\b",
)

_ALWAYS_UNSUPPORTED_PATTERNS = (
    r"\b(transfer|wire|remit|withdraw)\b",
    r"\b(send|move)\b.{0,35}\b(money|funds?|cash|dollars?|\$)\b",
    r"\b(pay|settle)\b.{0,35}\b(bill|invoice|merchant|person|someone|rent|debt)\b",
    r"\b(make|schedule)\b.{0,20}\bpayments?\b",
    r"\b(delete|erase|remove|close)\b.{0,35}\b(goal|profile|account|data|record)s?\b",
)
_EXECUTION_PATTERNS = (r"\b(buy|purchase|sell|trade|invest)\b",)

_CREATE_GOAL = re.compile(
    r"\b(create|add|start|set\s*up|make|open)\b.{0,45}\b(goal|fund)\b"
    r"|\b(goal|fund)\b.{0,45}\b(create|add|start|set\s*up|make|open)\b",
    re.IGNORECASE,
)

_PROFILE_FIELD_PATTERNS = {
    "currentBalance": (
        r"\bcurrent balance\b",
        r"\baccount balance\b",
        r"\bmy balance\b",
        r"\bbalance\b",
        r"\bavailable cash\b",
        r"\bhow much (?:money )?i (?:currently )?have\b(?!\s+saved\b)",
    ),
    "monthlyIncome": (
        r"\bmonthly income\b",
        r"\bincome per month\b",
        r"\bmonthly (?:salary|pay)\b",
        r"\b(?:salary|income|earnings|take-home pay)\b",
    ),
    "monthlyExpenses": (
        r"\bmonthly expenses?\b",
        r"\bexpenses? per month\b",
        r"\bmonthly (?:spending|costs?)\b",
        r"\b(?:expenses?|outgoings)\b",
        r"\bspend(?:ing)?\b.{0,20}\b(?:per|each|a) month\b",
    ),
}

_GOAL_FIELD_PATTERNS = {
    "name": (r"\brename\b", r"\bgoal name\b", r"\bname (?:my|the)\b"),
    "target": (
        r"\btarget\b",
        r"\bgoal amount\b",
        r"\b(?:goal|fund) (?:to|at|of|is)\b",
    ),
    "current": (
        r"\b(?:already |currently )?saved\b",
        r"\bsaved (?:amount|so far|toward|towards)\b",
        r"\bgoal progress\b",
        r"\bput aside\b",
        r"\b(?:goal|fund) (?:has|contains|currently has)\b",
    ),
    "monthlyContribution": (
        r"\bmonthly contribution\b",
        r"\bmonthly goal\b",
        r"\bmonthly (?:saving|savings) (?:amount|target|goal)\b",
        r"\bcontribut(?:e|ion)\b",
        r"\bsav(?:e|ing)\b.{0,25}\b(?:per|each|a) (?:month|week)\b",
        r"\b(?:put|add)\b.{0,25}\b(?:per|each|a) (?:month|week)\b",
    ),
}

_GOAL_REFERENCE = re.compile(
    r"\b(goal|fund|target|saved toward|saved towards|goal progress|contribution)\b",
    re.IGNORECASE,
)
_FOLLOW_UP_REFERENCE = re.compile(
    r"\b(it|that|this|the amount|the value|same goal|that goal)\b",
    re.IGNORECASE,
)
_MANAGE_INTENT = re.compile(
    r"\b(update|change|set|create|add|start|rename|saved|saving|contribution|"
    r"income|expenses?|balance|target)\b",
    re.IGNORECASE,
)
_NUMBER_VALUE = re.compile(r"(?<![\w.])\$?([0-9][\d,]*(?:\.\d+)?)")


@dataclass(frozen=True)
class ManageRequestPolicy:
    blocked_message: str | None = None
    create_goal: bool = False
    profile_fields: frozenset[str] = field(default_factory=frozenset)
    goal_fields: frozenset[str] = field(default_factory=frozenset)
    referenced_goal_ids: frozenset[str] = field(default_factory=frozenset)
    request_text: str = ""
    requested_numbers: tuple[float, ...] = ()


def _matches_any(text: str, patterns: tuple[str, ...]) -> bool:
    return any(re.search(pattern, text, re.IGNORECASE | re.DOTALL) for pattern in patterns)


def _referenced_goal_ids(context: str, profile: CustomerProfile) -> frozenset[str]:
    directly_matched = {
        goal.goalId
        for goal in profile.goals
        if re.search(
            rf"(?<!\w)(?:{re.escape(goal.goalId)}|{re.escape(goal.name)})(?!\w)",
            context,
            re.IGNORECASE,
        )
    }
    if directly_matched:
        return frozenset(directly_matched)

    generic_words = {"fund", "goal", "saving", "savings", "deposit"}
    aliases_by_goal = {
        goal.goalId: {
            word
            for word in re.findall(r"[a-z0-9]+", goal.name.casefold())
            if len(word) >= 4 and word not in generic_words
        }
        for goal in profile.goals
    }
    mentioned_aliases = {
        alias
        for aliases in aliases_by_goal.values()
        for alias in aliases
        if re.search(rf"(?<!\w){re.escape(alias)}(?!\w)", context, re.IGNORECASE)
    }
    unique_aliases = {
        alias
        for alias in mentioned_aliases
        if sum(alias in aliases for aliases in aliases_by_goal.values()) == 1
    }
    return frozenset(
        goal_id
        for goal_id, aliases in aliases_by_goal.items()
        if aliases & unique_aliases
    )


def _request_context(message: str, history: list[object]) -> str:
    text = message.strip()
    last_message = history[-1] if history else None
    follows_clarification = (
        len(text.split()) <= 12
        and getattr(last_message, "role", None) == "assistant"
        and "?" in getattr(last_message, "content", "")
    )
    if not _FOLLOW_UP_REFERENCE.search(text) and not follows_clarification:
        return text
    if follows_clarification:
        anchor = None
        for index in range(len(history) - 1, -1, -1):
            item = history[index]
            if (
                getattr(item, "role", None) == "user"
                and _MANAGE_INTENT.search(getattr(item, "content", ""))
            ):
                anchor = index
                break
        if anchor is not None:
            chain = [
                getattr(item, "content", "").strip()
                for item in history[anchor:]
                if getattr(item, "role", None) == "user"
                and getattr(item, "content", "").strip()
            ]
            return "\n".join([*chain, text])
    for item in reversed(history):
        if getattr(item, "role", None) == "user":
            return f"{getattr(item, 'content', '')}\n{text}"
    return text


def classify_manage_request(
    message: str,
    history: list[object],
    profile: CustomerProfile,
) -> ManageRequestPolicy:
    context = _request_context(message, history)
    if _matches_any(message, _INTERNAL_PATTERNS):
        return ManageRequestPolicy(blocked_message=INTERNAL_REQUEST_MESSAGE)

    goal_planning = bool(_CREATE_GOAL.search(context))
    if _matches_any(message, _ALWAYS_UNSUPPORTED_PATTERNS):
        return ManageRequestPolicy(blocked_message=UNSUPPORTED_OPERATION_MESSAGE)
    if _matches_any(message, _EXECUTION_PATTERNS) and not goal_planning:
        return ManageRequestPolicy(blocked_message=UNSUPPORTED_OPERATION_MESSAGE)

    profile_fields = frozenset(
        name
        for name, patterns in _PROFILE_FIELD_PATTERNS.items()
        if _matches_any(context, patterns)
    )
    goal_fields = frozenset(
        name
        for name, patterns in _GOAL_FIELD_PATTERNS.items()
        if _matches_any(context, patterns)
    )
    if (
        "monthlyContribution" in goal_fields
        and "target" in goal_fields
        and re.search(r"\bmonthly goal\b", context, re.IGNORECASE)
    ):
        goal_fields = frozenset(field for field in goal_fields if field != "target")
    referenced_goal_ids = _referenced_goal_ids(context, profile)
    requested_numbers = tuple(
        float(value.replace(",", ""))
        for value in _NUMBER_VALUE.findall(context)
    )
    return ManageRequestPolicy(
        create_goal=goal_planning,
        profile_fields=profile_fields,
        goal_fields=goal_fields,
        referenced_goal_ids=referenced_goal_ids,
        request_text=context,
        requested_numbers=requested_numbers,
    )


def _number_matches_request(
    value: float,
    current_value: float | None,
    policy: ManageRequestPolicy,
) -> bool:
    candidates = set(policy.requested_numbers)
    if current_value is not None and re.search(
        r"\b(increase|raise|add|more|decrease|reduce|lower|subtract|less)\b",
        policy.request_text,
        re.IGNORECASE,
    ):
        for amount in policy.requested_numbers:
            candidates.add(current_value + amount)
            candidates.add(current_value - amount)
    if re.search(r"\b(?:per|each|a)\s+week\b", policy.request_text, re.IGNORECASE):
        candidates.update(amount * 52 / 12 for amount in policy.requested_numbers)
    return any(abs(value - candidate) <= 0.02 for candidate in candidates)


def operations_match_request(
    operations: list[AgentOperation],
    policy: ManageRequestPolicy,
    profile: CustomerProfile,
) -> bool:
    for action in operations:
        if isinstance(action, CreateGoalOperation):
            if not policy.create_goal:
                return False
            numeric_values = (
                action.values.target,
                action.values.monthlyContribution,
            )
            if action.values.current:
                numeric_values += (action.values.current,)
            if len(policy.requested_numbers) < len(numeric_values):
                return False
            if any(
                not _number_matches_request(value, None, policy)
                for value in numeric_values
            ):
                return False
            continue
        if isinstance(action, SetProfileOperation):
            changed = action.value != getattr(profile, action.field)
            if changed and action.field not in policy.profile_fields:
                return False
            if not changed and action.field not in policy.profile_fields:
                return False
            if changed and not _number_matches_request(
                action.value,
                getattr(profile, action.field),
                policy,
            ):
                return False
            continue
        if isinstance(action, SetGoalOperation):
            goal = next(
                (item for item in profile.goals if item.goalId == action.resourceId),
                None,
            )
            if goal is None:
                return False
            changed = action.value != getattr(goal, action.field)
            if changed and action.field not in policy.goal_fields:
                return False
            if not changed and action.field not in policy.goal_fields:
                return False
            if policy.referenced_goal_ids and action.resourceId not in policy.referenced_goal_ids:
                return False
            if not policy.referenced_goal_ids:
                return False
            if (
                changed
                and action.field != "name"
                and not _number_matches_request(
                    float(action.value),
                    float(getattr(goal, action.field)),
                    policy,
                )
            ):
                return False
    return True
