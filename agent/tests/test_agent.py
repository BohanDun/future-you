from unittest.mock import patch

import pytest

from agent import parse_financial_question
from agent.fallback import generate_mock_explanation, unsupported_question_message
from agent.scenario_parser import parse_question_mock
from app.models.scenario import ParsedScenario


def test_mock_parser_handles_laptop_question() -> None:
    scenario = parse_question_mock("What happens if I buy a $2,000 laptop?")

    assert scenario.scenarioType == "one_off_purchase"
    assert scenario.amount == 2000
    assert scenario.description == "Laptop"


def test_mock_parser_handles_extra_savings_goal() -> None:
    scenario = parse_question_mock(
        "What if I save an extra $50 per week for my emergency fund?"
    )

    assert scenario.scenarioType == "extra_savings"
    assert scenario.goalId == "emergency_fund"
    assert scenario.frequency == "weekly"


@patch("agent.question_parser.invoke_bedrock")
def test_bedrock_parser_returns_validated_scenario(mock_invoke) -> None:
    mock_invoke.return_value = (
        '{"scenarioType":"one_off_purchase","amount":3000,'
        '"frequency":"one_time","description":"Japan trip",'
        '"goalId":"japan_holiday"}'
    )

    scenario = parse_financial_question("Can I afford a $3,000 trip to Japan next year?")

    assert scenario == ParsedScenario(
        scenarioType="one_off_purchase",
        amount=3000,
        frequency="one_time",
        description="Japan trip",
        goalId="japan_holiday",
    )


@patch("agent.question_parser.invoke_bedrock")
def test_bedrock_parser_falls_back_to_mock_on_failure(mock_invoke) -> None:
    mock_invoke.side_effect = RuntimeError("Bedrock unavailable")

    scenario = parse_financial_question("What happens if I buy a $2,000 laptop?")

    assert scenario.scenarioType == "one_off_purchase"
    assert scenario.amount == 2000


def test_mock_explanation_uses_calculated_numbers(alex, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services.simulation_service import run_simulation

    scenario = parse_question_mock("What happens if I buy a $2,000 laptop?")
    result = run_simulation(alex, scenario)
    explanation = generate_mock_explanation(alex, scenario, result)

    assert "$8,000.00 to $6,000.00" in explanation
    assert "delayed by 2 months" in explanation
    assert result.riskLevel in explanation


def test_unsupported_question_fallback_message() -> None:
    message = unsupported_question_message()

    assert "what-if" in message.lower()
    assert "$2,000 laptop" in message
