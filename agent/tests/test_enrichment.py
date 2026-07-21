import pytest

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


def test_next_year_is_preserved_as_a_twelve_month_horizon() -> None:
    scenario = parse_financial_question("Can I afford a $3,000 trip next year?")

    assert scenario.horizonMonths == 12
    assert scenario.timingLabel == "next year"


def test_horizon_number_is_not_mistaken_for_purchase_amount() -> None:
    scenario = parse_financial_question("Can I afford a trip in 6 months?")

    assert scenario.horizonMonths == 6
    assert scenario.amount == 3500


@pytest.mark.parametrize(
    ("question", "expected_months"),
    [
        ("What about 2 months later?", 2),
        ("What about two months later?", 2),
        ("What about after 3 months?", 3),
        ("What about 6 months from now?", 6),
        ("Could I buy it 2 years from now?", 24),
    ],
)
def test_relative_time_phrases_are_understood(
    question: str,
    expected_months: int,
) -> None:
    scenario = parse_question_mock(question)

    assert scenario.horizonMonths == expected_months
