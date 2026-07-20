import logging

from agent.bedrock_client import invoke_bedrock
from agent.prompts import EXPLANATION_SYSTEM
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
    user_prompt = f"""
Original question:
{question_line}

Customer:
{customer.model_dump_json()}

Scenario:
{scenario.model_dump_json()}

Simulation result:
{result.model_dump_json()}
""".strip()

    return invoke_bedrock(
        system_prompt=EXPLANATION_SYSTEM,
        user_prompt=user_prompt,
        max_tokens=450,
        temperature=0.35,
    )
