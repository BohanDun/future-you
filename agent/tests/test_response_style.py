from unittest.mock import patch

from agent.coach import answer_freeform_question
from agent.explainer import explain_with_bedrock
from agent.response_style import normalize_chat_response
from agent.scenario_parser import parse_question_mock
from app.services.simulation_service import run_simulation


def test_chat_response_removes_email_wrapper_and_extra_spacing() -> None:
    response = normalize_chat_response(
        """Hi Peter,

The simulation shows that the trip carries a High risk.

Saving a little longer would protect your emergency buffer.

Best,
[Your Name]"""
    )

    assert response == (
        "The simulation shows that the trip carries a High risk. "
        "Saving a little longer would protect your emergency buffer."
    )


def test_chat_response_removes_inline_greeting_without_losing_answer() -> None:
    assert normalize_chat_response(
        "Hello Alex, your monthly savings would increase by $200."
    ) == "your monthly savings would increase by $200."


def test_freeform_coach_normalizes_bedrock_output(alex) -> None:
    with (
        patch("agent.config.get_ai_mode", return_value="bedrock"),
        patch(
            "agent.coach.invoke_bedrock",
            return_value=(
                "Hi Alex,\n\nStart with a three-month emergency buffer."
                "\n\nRegards,\nFuture You"
            ),
        ),
    ):
        response = answer_freeform_question(alex, "How should I start saving?")

    assert response == "Start with a three-month emergency buffer."


def test_simulation_explanation_normalizes_bedrock_output(alex) -> None:
    scenario = parse_question_mock("What if I buy a $2,000 laptop?")
    result = run_simulation(alex, scenario)
    with patch(
        "agent.explainer.invoke_bedrock",
        return_value=(
            "Hi Alex,\n\nThis purchase has a Medium risk. "
            "Consider waiting a little longer.\n\nBest,\n[Your Name]"
        ),
    ):
        response = explain_with_bedrock(alex, scenario, result)

    assert response == (
        "This purchase has a Medium risk. Consider waiting a little longer."
    )


def test_simulation_explanation_rejects_invented_numbers(alex) -> None:
    scenario = parse_question_mock("What if I buy a $2,000 laptop?")
    result = run_simulation(alex, scenario)
    with patch(
        "agent.explainer.invoke_bedrock",
        return_value="Your balance will be $99,999 and the risk is Medium.",
    ):
        response = explain_with_bedrock(alex, scenario, result)

    assert "$99,999" not in response
    assert result.riskLevel in response
