import logging

from agent.bedrock_client import invoke_bedrock
from agent.prompts import GENERAL_COACH_SYSTEM
from app.models.customer import CustomerProfile

logger = logging.getLogger(__name__)


def answer_freeform_question(
    customer: CustomerProfile,
    question: str,
) -> str:
    from agent.config import get_ai_mode

    if get_ai_mode() != "bedrock":
        return generate_mock_coach_response(customer, question)

    user_prompt = f"""
Customer profile:
{customer.model_dump_json()}

Question:
{question.strip()}
""".strip()

    try:
        return invoke_bedrock(
            system_prompt=GENERAL_COACH_SYSTEM,
            user_prompt=user_prompt,
            max_tokens=550,
            temperature=0.55,
        )
    except Exception as exc:
        logger.error("Bedrock coach response failed", exc_info=True)
        raise RuntimeError("Bedrock coach response failed") from exc
