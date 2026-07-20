import logging

from agent.bedrock_client import invoke_bedrock
from agent.json_utils import parse_json_object
from agent.prompts import QUESTION_PARSER_SYSTEM
from app.models.scenario import ParsedScenario

logger = logging.getLogger(__name__)


def parse_question_with_bedrock(question: str) -> ParsedScenario:
    user_prompt = f"Question: {question.strip()}"

    response_text = invoke_bedrock(
        system_prompt=QUESTION_PARSER_SYSTEM,
        user_prompt=user_prompt,
        max_tokens=250,
    )
    response_data = parse_json_object(response_text)
    scenario = ParsedScenario.model_validate(response_data)
    if scenario.scenarioType == "unknown":
        logger.info("Bedrock classified question as unsupported scenario")
    return scenario
