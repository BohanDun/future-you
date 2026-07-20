from agent.fallback import generate_mock_coach_response
from agent.service import can_run_simulation
from app.models.scenario import ParsedScenario


def test_can_run_simulation_requires_known_type_and_amount() -> None:
    assert can_run_simulation(
        ParsedScenario(
            scenarioType="one_off_purchase",
            amount=2000,
            frequency="one_time",
            description="Laptop",
        )
    )
    assert not can_run_simulation(
        ParsedScenario(scenarioType="unknown", amount=None)
    )
    assert not can_run_simulation(
        ParsedScenario(
            scenarioType="one_off_purchase",
            amount=0,
            frequency="one_time",
        )
    )


def test_mock_coach_handles_stock_question(alex) -> None:
    reply = generate_mock_coach_response(
        alex,
        "I want to buy stocks, do you have any recommendations?",
    )

    assert "stock" in reply.lower() or "invest" in reply.lower()
    assert alex.name in reply


def test_mock_coach_handles_bank_account_question(alex) -> None:
    reply = generate_mock_coach_response(
        alex,
        "I want to open a bank account, how do I do that?",
    )

    assert "account" in reply.lower()
    assert alex.name in reply
