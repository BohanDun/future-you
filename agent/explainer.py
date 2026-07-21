import logging

from agent.bedrock_client import invoke_bedrock
from agent.fallback import generate_mock_explanation
from agent.grounding import explanation_is_grounded
from agent.prompts import EXPLANATION_SYSTEM
from agent.response_style import normalize_chat_response
from app.models.customer import CustomerProfile
from app.models.scenario import ParsedScenario
from app.models.simulation import SimulationResult

logger = logging.getLogger(__name__)


def explain_with_bedrock(
    customer: CustomerProfile,
    scenario: ParsedScenario,
    result: SimulationResult,
    question: str | None = None,
) -> str:
    question_line = question.strip() if question else "Not provided"
    profile_context = customer.model_dump_json(include={"currency", "goals"})
    user_prompt = f"""
Original question:
{question_line}

Customer:
{profile_context}

Scenario:
{scenario.model_dump_json()}

Simulation result:
{result.model_dump_json()}
""".strip()

    try:
        response = invoke_bedrock(
            system_prompt=EXPLANATION_SYSTEM,
            user_prompt=user_prompt,
            max_tokens=450,
            temperature=0.35,
        )
        normalized = normalize_chat_response(response)
        if normalized and explanation_is_grounded(normalized, customer, scenario, result):
            return normalized
        logger.warning("Bedrock explanation contained an unverified numeric claim")
        return generate_mock_explanation(customer, scenario, result, question=question)
    except Exception:
        logger.warning(
            "Bedrock explanation generation failed; using mock explanation",
            exc_info=True,
        )
        return generate_mock_explanation(
            customer, scenario, result, question=question
        )
