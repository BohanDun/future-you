import logging

from agent.bedrock_client import invoke_bedrock
from agent.fallback import unsupported_question_message
from agent.json_utils import parse_json_object
from agent.prompts import QUESTION_PARSER_SYSTEM
from agent.scenario_parser import parse_question_mock
from app.models.scenario import ParsedScenario

logger = logging.getLogger(__name__)


def parse_question_with_bedrock(question: str) -> ParsedScenario:
    user_prompt = f"Question: {question.strip()}"

    try:
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
    except Exception:
        logger.warning(
            "Bedrock question parsing failed; using mock parser",
            exc_info=True,
        )
        return parse_question_mock(question)


def fallback_for_unsupported_question() -> str:
    return unsupported_question_message()
