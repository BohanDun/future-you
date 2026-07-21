import logging

from agent.bedrock_client import invoke_bedrock
from agent.fallback import generate_mock_coach_response
from agent.prompts import GENERAL_COACH_SYSTEM
from agent.response_style import normalize_chat_response
from app.models.agent_action import ConversationMessage
from app.models.customer import CustomerProfile

logger = logging.getLogger(__name__)


def answer_freeform_question(
    customer: CustomerProfile,
    question: str,
    history: list[ConversationMessage] | None = None,
) -> str:
    from agent.config import get_ai_mode

    if get_ai_mode() != "bedrock":
        return generate_mock_coach_response(customer, question)

    transcript = "\n".join(
        f"{item.role.title()}: {item.content}"
        for item in (history or [])[-12:]
    )
    profile_context = customer.model_dump_json(include={
        "currency",
        "currentBalance",
        "monthlyIncome",
        "monthlyExpenses",
        "monthlySavings",
        "goals",
        "spendingCategories",
        "insights",
    })
    user_prompt = f"""
Customer profile:
{profile_context}

Recent conversation:
{transcript or "No earlier messages."}

Question:
{question.strip()}
""".strip()

    try:
        response = invoke_bedrock(
            system_prompt=GENERAL_COACH_SYSTEM,
            user_prompt=user_prompt,
            max_tokens=550,
            temperature=0.55,
        )
        return normalize_chat_response(response) or generate_mock_coach_response(
            customer, question
        )
    except Exception:
        logger.warning(
            "Bedrock coach response failed; using mock coach",
            exc_info=True,
        )
        return generate_mock_coach_response(customer, question)
