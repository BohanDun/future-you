import logging
import re
from typing import Any

from pydantic import TypeAdapter, ValidationError

from agent.bedrock_client import invoke_bedrock_with_tools
from agent.config import get_ai_mode
from agent.manage_policy import (
    MISMATCH_MESSAGE,
    ManageRequestPolicy,
    classify_manage_request,
    operations_match_request,
)
from agent.response_style import normalize_chat_response
from app.models.agent_action import (
    AgentOperation,
    ClarificationRequest,
    ConversationMessage,
    CreateGoalOperation,
    GoalValues,
    ManageAgentResponse,
    SetGoalOperation,
    SetProfileOperation,
)
from app.models.customer import CustomerProfile
from app.services.agent_action_service import preview_agent_operations
from app.services.proposal_service import ProposalTokenError, create_proposal_token

logger = logging.getLogger(__name__)
_operation_adapter = TypeAdapter(AgentOperation)

MANAGE_SYSTEM = """You are the action-planning mode of Future You, a financial wellbeing app.
You may propose changes to the authenticated customer's profile using only the provided tools.
Never claim that a change has already been applied. Tool calls create reviewable proposals only.

Voice and tone:
- Be warm, calm, and collaborative, like a thoughtful financial coach.
- Use natural, concise English. Acknowledge the customer's goal without sounding robotic.
- Avoid legalistic or technical language. Never scold the customer.
- Reply like a chat assistant. Do not use greetings, email sign-offs, signatures, or
  template placeholders.

Rules:
- Use create_goal to propose a new savings goal.
- Use update_profile to change current balance, monthly income, or monthly expenses.
- Use update_goal to change an existing goal. Copy goalId exactly from the profile.
- Treat "monthly goal" as the customer's monthlyContribution for that goal.
- Monthly savings is calculated automatically; never try to change it directly.
- Build on facts the customer supplied earlier in this conversation. Do not ask again
  for fields that are already clear.
- Do not invent a goal name, target, or monthly contribution. create_goal may be called
  with only the fields currently known; the application will ask for exactly the missing
  fields. Assume current is 0 unless the customer says they have already saved something.
- When information is ambiguous, call request_clarification with the missing field names
  and one concise, customer-facing question.
- Output only the customer-facing response. Never output analysis, reasoning, or thinking tags.
- Treat a number as a replacement value unless the customer explicitly says increase/decrease/by.
- Never create, select, or modify a user ID.
- Do not propose deletion, transactions, transfers, purchases, or investments.
- You may make multiple tool calls when the customer clearly requests multiple changes.
- If the customer only wants advice, answer briefly and explain that Advice mode is better suited.
"""

TOOLS = [
    {
        "toolSpec": {
            "name": "create_goal",
            "description": "Propose creating a new financial goal.",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "target": {"type": "number", "exclusiveMinimum": 0},
                        "current": {"type": "number", "minimum": 0},
                        "monthlyContribution": {"type": "number", "minimum": 0},
                    },
                }
            },
        }
    },
    {
        "toolSpec": {
            "name": "update_profile",
            "description": "Propose changing balance, monthly income, or monthly expenses.",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "currentBalance": {"type": "number", "minimum": 0},
                        "monthlyIncome": {"type": "number", "minimum": 0},
                        "monthlyExpenses": {"type": "number", "minimum": 0},
                    },
                }
            },
        }
    },
    {
        "toolSpec": {
            "name": "update_goal",
            "description": "Propose changing an existing financial goal.",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "goalId": {"type": "string"},
                        "name": {"type": "string"},
                        "target": {"type": "number", "exclusiveMinimum": 0},
                        "current": {"type": "number", "minimum": 0},
                        "monthlyContribution": {"type": "number", "minimum": 0},
                    },
                    "required": ["goalId"],
                }
            },
        }
    },
    {
        "toolSpec": {
            "name": "request_clarification",
            "description": (
                "Request missing or ambiguous information before preparing a change."
            ),
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "missingFields": {
                            "type": "array",
                            "items": {"type": "string"},
                            "minItems": 1,
                            "maxItems": 8,
                        },
                        "question": {"type": "string"},
                    },
                    "required": ["missingFields", "question"],
                }
            },
        }
    },
]


def _bedrock_messages(
    history: list[ConversationMessage],
    message: str,
    profile: CustomerProfile,
) -> list[dict[str, Any]]:
    recent_history = history[-12:]
    first_user = next(
        (index for index, item in enumerate(recent_history) if item.role == "user"),
        len(recent_history),
    )
    messages: list[dict[str, Any]] = []
    for item in recent_history[first_user:]:
        if messages and messages[-1]["role"] == item.role:
            previous_text = messages[-1]["content"][0]["text"]
            messages[-1]["content"][0]["text"] = (
                f"{previous_text}\n{item.content}"
            )
        else:
            messages.append(
                {
                    "role": item.role,
                    "content": [{"text": item.content}],
                }
            )
    profile_context = profile.model_dump_json(
        include={
            "currency",
            "currentBalance",
            "monthlyIncome",
            "monthlyExpenses",
            "monthlySavings",
            "goals",
        }
    )
    request_text = (
        f"Current profile (trusted application data):\n{profile_context}\n\n"
        f"Customer request:\n{message.strip()}"
    )
    if messages and messages[-1]["role"] == "user":
        previous_text = messages[-1]["content"][0]["text"]
        messages[-1]["content"][0]["text"] = f"{previous_text}\n{request_text}"
    else:
        messages.append(
            {
                "role": "user",
                "content": [{"text": request_text}],
            }
        )
    return messages


def _operations_from_tool(
    tool_name: str,
    tool_input: dict[str, Any],
) -> list[AgentOperation]:
    if tool_name == "create_goal":
        return [_operation_adapter.validate_python({
            "operation": "create",
            "resource": "goal",
            "values": tool_input,
        })]
    if tool_name == "update_profile":
        return [
            _operation_adapter.validate_python({
                "operation": "set",
                "resource": "profile",
                "field": field,
                "value": value,
            })
            for field, value in tool_input.items()
        ]
    if tool_name == "update_goal":
        goal_id = tool_input.get("goalId")
        return [
            _operation_adapter.validate_python({
                "operation": "set",
                "resource": "goal",
                "resourceId": goal_id,
                "field": field,
                "value": value,
            })
            for field, value in tool_input.items()
            if field != "goalId"
        ]
    raise ValueError(f"Unknown agent tool: {tool_name}")


def _goal_draft_clarification(
    tool_input: dict[str, Any],
) -> ClarificationRequest | None:
    missing: list[str] = []
    name = tool_input.get("name")
    if not isinstance(name, str) or not name.strip():
        missing.append("name")
    target = tool_input.get("target")
    if isinstance(target, bool) or not isinstance(target, (int, float)):
        missing.append("target")
    monthly = tool_input.get("monthlyContribution")
    if isinstance(monthly, bool) or not isinstance(monthly, (int, float)):
        missing.append("monthlyContribution")
    if not missing:
        return None

    questions = {
        "name": "what you’d like to call the goal",
        "target": "the total amount you’re aiming for",
        "monthlyContribution": "how much you’d like to add each month (which can be $0)",
    }
    details = [questions[field] for field in missing]
    if len(details) == 1:
        requested = details[0]
    else:
        requested = f"{', '.join(details[:-1])}, and {details[-1]}"
    return ClarificationRequest(
        missingFields=missing,
        question=f"Got it — could you tell me {requested}?",
    )


def _mock_goal_name(request_text: str) -> str:
    lowered = request_text.casefold()
    patterns = (
        r"\bcall it\s+([a-z][a-z ]*?)(?:\s+and\b|[,.;\n]|$)",
        r"\bgoal\s+(?:called|named)\s+([a-z][a-z ]*?)(?:\s+with\b|[,.;\n]|$)",
        r"\bcreate\s+(?:a|an)\s+(?:\$?[\d,]+(?:\.\d+)?\s+)?"
        r"([a-z][a-z ]*?)\s+goal\b",
        r"\bgoal\s+to\s+([a-z][a-z ]*?)(?:\s+for\s+\$|[,.;\n]|$)",
    )
    for pattern in patterns:
        match = re.search(pattern, lowered)
        if match:
            name = re.sub(r"\s+", " ", match.group(1)).strip()
            if name and name not in {"a", "an", "new", "saving", "savings"}:
                return name.title()
    return "Savings Goal"


def _mock_requested_value(
    policy: ManageRequestPolicy,
    current: float,
) -> float:
    amount = policy.requested_numbers[-1]
    if re.search(r"\b(?:per|each|a)\s+week\b", policy.request_text, re.IGNORECASE):
        amount = round(amount * 52 / 12, 2)
    if re.search(r"\b(increase|raise|add|more)\b", policy.request_text, re.IGNORECASE):
        return round(current + amount, 2)
    if re.search(
        r"\b(decrease|reduce|lower|subtract|less)\b",
        policy.request_text,
        re.IGNORECASE,
    ):
        return round(current - amount, 2)
    return amount


def _mock_plan(
    profile: CustomerProfile,
    policy: ManageRequestPolicy,
) -> tuple[str, list[AgentOperation]]:
    if policy.create_goal and len(policy.requested_numbers) >= 2:
        operation = CreateGoalOperation(
            operation="create",
            resource="goal",
            values=GoalValues(
                name=_mock_goal_name(policy.request_text),
                target=policy.requested_numbers[0],
                current=0,
                monthlyContribution=policy.requested_numbers[1],
            ),
        )
        return "Great — I’ve drafted that new goal for you to review.", [operation]
    if (
        len(policy.profile_fields) == 1
        and policy.requested_numbers
    ):
        field = next(iter(policy.profile_fields))
        operation = SetProfileOperation(
            operation="set",
            resource="profile",
            field=field,
            value=_mock_requested_value(policy, float(getattr(profile, field))),
        )
        return "I’ve drafted that profile update for you to review.", [operation]
    if (
        len(policy.goal_fields) == 1
        and len(policy.referenced_goal_ids) == 1
        and policy.requested_numbers
    ):
        field = next(iter(policy.goal_fields))
        goal_id = next(iter(policy.referenced_goal_ids))
        goal = next(goal for goal in profile.goals if goal.goalId == goal_id)
        operation = SetGoalOperation(
            operation="set",
            resource="goal",
            resourceId=goal_id,
            field=field,
            value=_mock_requested_value(policy, float(getattr(goal, field))),
        )
        return "I’ve drafted that goal update for you to review.", [operation]
    return (
        "I can help with that. Tell me which figure or goal you’d like to change, "
        "along with the new amount.",
        [],
    )


def _customer_facing_text(text: str) -> str:
    cleaned = re.sub(
        r"<(thinking|analysis|reasoning)>.*?</\1>",
        "",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    return normalize_chat_response(cleaned)


def _generic_clarification_message() -> str:
    return (
        "I’m happy to help — which figure or goal would you like to change, and "
        "what should the new value be?"
    )


def _remove_unchanged_operations(
    profile: CustomerProfile,
    operations: list[AgentOperation],
) -> list[AgentOperation]:
    changed: list[AgentOperation] = []
    goals = {goal.goalId: goal for goal in profile.goals}
    for item in operations:
        if isinstance(item, CreateGoalOperation):
            changed.append(item)
        elif isinstance(item, SetProfileOperation):
            if item.value != getattr(profile, item.field):
                changed.append(item)
        elif isinstance(item, SetGoalOperation):
            goal = goals.get(item.resourceId)
            if goal is None or item.value != getattr(goal, item.field):
                changed.append(item)
    return changed


def plan_profile_changes(
    profile: CustomerProfile,
    message: str,
    history: list[ConversationMessage],
) -> ManageAgentResponse:
    policy = classify_manage_request(message, history, profile)
    if policy.blocked_message:
        return ManageAgentResponse(message=policy.blocked_message)

    ai_mode = get_ai_mode()
    clarifications: list[ClarificationRequest] = []
    if ai_mode != "bedrock":
        if policy.create_goal and len(policy.requested_numbers) < 2:
            partial_input = (
                {"target": policy.requested_numbers[0]}
                if policy.requested_numbers
                else {}
            )
            clarification = _goal_draft_clarification(partial_input)
            if clarification is not None:
                return ManageAgentResponse(
                    message=clarification.question,
                    clarification=clarification,
                )
        response_message, operations = _mock_plan(profile, policy)
    else:
        try:
            content = invoke_bedrock_with_tools(
                system_prompt=MANAGE_SYSTEM,
                messages=_bedrock_messages(history, message, profile),
                tools=TOOLS,
            )
            operations = []
            text_parts = []
            for block in content:
                if "text" in block:
                    customer_text = _customer_facing_text(block["text"])
                    if customer_text:
                        text_parts.append(customer_text)
                if "toolUse" in block:
                    tool = block["toolUse"]
                    if tool["name"] == "request_clarification":
                        clarifications.append(
                            ClarificationRequest.model_validate(tool["input"])
                        )
                    elif tool["name"] == "create_goal":
                        clarification = _goal_draft_clarification(tool["input"])
                        if clarification is not None:
                            clarifications.append(clarification)
                        else:
                            goal_input = {"current": 0, **tool["input"]}
                            operations.extend(
                                _operations_from_tool(tool["name"], goal_input)
                            )
                    else:
                        operations.extend(
                            _operations_from_tool(tool["name"], tool["input"])
                        )
            response_message = " ".join(part for part in text_parts if part)
        except (ValidationError, ValueError, KeyError, TypeError):
            logger.warning("Invalid manage-mode tool response", exc_info=True)
            return ManageAgentResponse(
                message=(
                    "I couldn’t turn that into a clear update just yet. Tell me which "
                    "figure or goal you’d like to change and the new value you want."
                ),
            )
        except Exception:
            logger.warning("Bedrock manage-mode request failed", exc_info=True)
            return ManageAgentResponse(
                message=(
                    "I’m having trouble reaching the planning service right now. "
                    "Please try again in a moment."
                ),
            )

    if clarifications:
        raw_clarification = clarifications[0]
        clarification = ClarificationRequest(
            missingFields=raw_clarification.missingFields,
            question=(
                _customer_facing_text(raw_clarification.question)
                or _generic_clarification_message()
            ),
        )
        return ManageAgentResponse(
            message=clarification.question,
            clarification=clarification,
        )
    if not operations:
        return ManageAgentResponse(
            message=response_message or _generic_clarification_message(),
        )
    operations = _remove_unchanged_operations(profile, operations)
    if not operations:
        return ManageAgentResponse(
            message=(
                "You’re already set — your profile already has that value, so "
                "there’s nothing to change."
            )
        )
    if not operations_match_request(operations, policy, profile):
        logger.warning("Manage-mode actions did not match the customer's request")
        if policy.create_goal:
            clarification = ClarificationRequest(
                missingFields=["name", "target", "monthlyContribution"],
                question=(
                    "I understand you want to create a goal, but I don’t want to "
                    "guess how the amounts should be used. What should the goal be "
                    "called, what is its total target, and how much would you like "
                    "to add each month?"
                ),
            )
            return ManageAgentResponse(
                message=clarification.question,
                clarification=clarification,
            )
        return ManageAgentResponse(message=MISMATCH_MESSAGE)
    try:
        preview = preview_agent_operations(profile, operations)
    except ValueError as exc:
        return ManageAgentResponse(message=f"I couldn’t prepare that change: {exc}")
    try:
        proposal_token = create_proposal_token(profile, operations)
    except ProposalTokenError:
        logger.error("Manage proposal signing is not configured", exc_info=True)
        return ManageAgentResponse(
            message=(
                "I can’t prepare a secure preview right now because the planning "
                "service is not fully configured."
            )
        )
    return ManageAgentResponse(
        message=(
            "Here’s what I’ve prepared. Take a look, and only confirm if it feels "
            "right — nothing has been saved yet."
        ),
        operations=operations,
        preview=preview,
        proposalToken=proposal_token,
    )
