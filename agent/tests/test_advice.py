from unittest.mock import patch

from agent.advice import route_advice_question
from app.models.agent_action import ConversationMessage
from app.models.customer import FinancialGoal


def test_mock_advice_router_targets_a_dynamic_goal(alex) -> None:
    profile = alex.model_copy(deep=True)
    profile.goals.append(FinancialGoal(
        goalId="new_car_2027",
        name="New Car",
        target=20_000,
        current=2_000,
        monthlyContribution=500,
    ))

    route = route_advice_question(
        profile,
        "What if I save an extra $100 per week for my New Car goal?",
    )

    assert route.kind == "simulation"
    assert route.scenario is not None
    assert route.scenario.goalId == "new_car_2027"


def test_mock_advice_router_separates_off_topic_and_financial_advice(alex) -> None:
    assert route_advice_question(alex, "How do I cook dinner?").kind == "off_topic"
    assert route_advice_question(alex, "How should I diversify investments?").kind == (
        "financial_advice"
    )


def test_mock_advice_router_resolves_a_timing_only_follow_up(alex) -> None:
    history = [
        ConversationMessage(
            role="user",
            content="What happens if I buy a $2,000 laptop?",
        ),
        ConversationMessage(
            role="assistant",
            content="Buying it today would leave you with $6,000.",
        ),
    ]

    route = route_advice_question(alex, "What about next month?", history)

    assert route.kind == "simulation"
    assert route.scenario is not None
    assert route.scenario.amount == 2000
    assert route.scenario.description == "Laptop"
    assert route.scenario.horizonMonths == 1
    assert route.scenario.timingLabel == "next month"


def test_mock_advice_router_resolves_months_later_follow_up(alex) -> None:
    history = [
        ConversationMessage(
            role="user",
            content="What happens if I buy a $2,000 laptop?",
        ),
        ConversationMessage(
            role="assistant",
            content="Buying it today would leave you with $6,000.",
        ),
    ]

    route = route_advice_question(alex, "What about 2 months later?", history)

    assert route.kind == "simulation"
    assert route.scenario is not None
    assert route.scenario.amount == 2000
    assert route.scenario.description == "Laptop"
    assert route.scenario.horizonMonths == 2
    assert route.scenario.timingLabel == "2 months later"


def test_bedrock_is_used_before_the_follow_up_fallback(alex) -> None:
    history = [
        ConversationMessage(
            role="user",
            content="What happens if I buy a $2,000 laptop?",
        ),
        ConversationMessage(role="assistant", content="Here is the simulation."),
    ]
    with (
        patch("agent.advice.get_ai_mode", return_value="bedrock"),
        patch(
            "agent.advice.invoke_bedrock",
            return_value=(
                '{"kind":"simulation","scenario":{'
                '"scenarioType":"one_off_purchase","amount":2000,'
                '"frequency":"one_time","description":"Laptop","goalId":null,'
                '"horizonMonths":2,"timingLabel":"2 months later"}}'
            ),
        ) as invoke,
    ):
        route = route_advice_question(alex, "What about 2 months later?", history)

    invoke.assert_called_once()
    assert route.scenario is not None
    assert route.scenario.horizonMonths == 2


def test_bedrock_follow_up_cannot_change_an_unmentioned_amount(alex) -> None:
    history = [
        ConversationMessage(
            role="user",
            content="What happens if I buy a $2,000 laptop?",
        ),
        ConversationMessage(role="assistant", content="Here is the simulation."),
    ]
    with (
        patch("agent.advice.get_ai_mode", return_value="bedrock"),
        patch(
            "agent.advice.invoke_bedrock",
            return_value=(
                '{"kind":"simulation","scenario":{'
                '"scenarioType":"one_off_purchase","amount":9000,'
                '"frequency":"one_time","description":"Laptop","goalId":null,'
                '"horizonMonths":2,"timingLabel":"2 months later"}}'
            ),
        ),
    ):
        route = route_advice_question(alex, "What about 2 months later?", history)

    assert route.scenario is not None
    assert route.scenario.amount == 2000


def test_bedrock_misclassified_follow_up_falls_back_to_the_previous_scenario(alex) -> None:
    history = [
        ConversationMessage(
            role="user",
            content="What happens if I buy a $2,000 laptop?",
        ),
        ConversationMessage(role="assistant", content="Here is the simulation."),
    ]
    with (
        patch("agent.advice.get_ai_mode", return_value="bedrock"),
        patch(
            "agent.advice.invoke_bedrock",
            return_value='{"kind":"financial_advice","scenario":null}',
        ),
    ):
        route = route_advice_question(alex, "What about 2 months later?", history)

    assert route.kind == "simulation"
    assert route.scenario is not None
    assert route.scenario.amount == 2000
    assert route.scenario.horizonMonths == 2


def test_bedrock_can_change_the_subject_of_a_follow_up(alex) -> None:
    history = [
        ConversationMessage(
            role="user",
            content="What happens if I buy a $2,000 laptop?",
        ),
        ConversationMessage(role="assistant", content="Here is the simulation."),
    ]
    with (
        patch("agent.advice.get_ai_mode", return_value="bedrock"),
        patch(
            "agent.advice.invoke_bedrock",
            return_value=(
                '{"kind":"simulation","scenario":{'
                '"scenarioType":"one_off_purchase","amount":1200,'
                '"frequency":"one_time","description":"Phone","goalId":null,'
                '"horizonMonths":0,"timingLabel":null}}'
            ),
        ),
    ):
        route = route_advice_question(alex, "What about a phone instead?", history)

    assert route.scenario is not None
    assert route.scenario.description == "Phone"
    assert route.scenario.amount == 1200
