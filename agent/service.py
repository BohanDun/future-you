"""Public agent API used by the backend simulate endpoint."""

from agent.coach import answer_freeform_question
from agent.config import get_ai_mode
from agent.enrichment import enrich_scenario
from agent.explainer import explain_with_bedrock
from agent.fallback import generate_mock_explanation
from agent.question_parser import parse_question_with_bedrock
from agent.scenario_parser import parse_question_mock
from app.models.customer import CustomerProfile
from app.models.scenario import ParsedScenario
from app.models.simulation import SimulationResult


def can_run_simulation(scenario: ParsedScenario) -> bool:
    return (
        scenario.scenarioType != "unknown"
        and scenario.amount is not None
        and scenario.amount > 0
    )


def parse_financial_question(question: str) -> ParsedScenario:
    if get_ai_mode() != "bedrock":
        scenario = parse_question_mock(question)
    else:
        scenario = parse_question_with_bedrock(question)
    return enrich_scenario(question, scenario)


def generate_explanation(
    customer: CustomerProfile,
    scenario: ParsedScenario,
    result: SimulationResult,
    question: str | None = None,
) -> str:
    if get_ai_mode() != "bedrock":
        return generate_mock_explanation(
            customer, scenario, result, question=question
        )
    return explain_with_bedrock(
        customer, scenario, result, question=question
    )


__all__ = [
    "answer_freeform_question",
    "can_run_simulation",
    "generate_explanation",
    "parse_financial_question",
]
