from agent.enrichment import enrich_scenario
from agent.scenario_parser import parse_question_mock
from agent.service import parse_financial_question


def test_enrichment_infers_laptop_amount_without_price() -> None:
    scenario = enrich_scenario(
        "What happens if I buy a laptop?",
        parse_question_mock("What happens if I buy a laptop?"),
    )

    assert scenario.amount == 2000
    assert "estimated $2,000" in scenario.description


def test_enrichment_keeps_explicit_amount() -> None:
    scenario = enrich_scenario(
        "What happens if I buy a $900 laptop?",
        parse_question_mock("What happens if I buy a $900 laptop?"),
    )

    assert scenario.amount == 900
    assert "estimated" not in (scenario.description or "").lower()


def test_parse_financial_question_enriches_in_mock_mode() -> None:
    scenario = parse_financial_question("What happens if I buy a laptop?")

    assert scenario.scenarioType == "one_off_purchase"
    assert scenario.amount == 2000
