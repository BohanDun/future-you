import json
import logging
import os
from typing import Any

import boto3

from app.agent.scenario_parser import parse_question_mock
from app.models.customer import CustomerProfile
from app.models.scenario import ParsedScenario
from app.models.simulation import SimulationResult

logger = logging.getLogger(__name__)

AI_MODE = os.getenv("AI_MODE", "mock").strip().lower()
AWS_REGION = os.getenv("AWS_REGION_NAME", "ap-southeast-2")
BEDROCK_MODEL_ID = os.getenv(
    "BEDROCK_MODEL_ID",
    "amazon.nova-lite-v1:0",
)


def _invoke_bedrock(prompt: str, max_tokens: int) -> str:
    client = boto3.client(
        "bedrock-runtime",
        region_name=AWS_REGION,
    )
    response = client.converse(
        modelId=BEDROCK_MODEL_ID,
        messages=[
            {
                "role": "user",
                "content": [{"text": prompt}],
            }
        ],
        inferenceConfig={
            "maxTokens": max_tokens,
            "temperature": 0.1,
        },
    )

    content = response["output"]["message"]["content"]
    text_parts = [
        block["text"]
        for block in content
        if "text" in block
    ]

    if not text_parts:
        raise ValueError("Bedrock returned no text content")

    return "".join(text_parts).strip()


def _parse_json_object(text: str) -> dict[str, Any]:
    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1 or end < start:
        raise ValueError("Bedrock returned no JSON object")

    value = json.loads(text[start : end + 1])

    if not isinstance(value, dict):
        raise ValueError("Bedrock JSON response is not an object")

    return value


def parse_financial_question(
    question: str,
) -> ParsedScenario:
    if AI_MODE != "bedrock":
        return parse_question_mock(question)

    prompt = f"""
Classify the financial what-if question below. Return only one JSON object
with these fields:
- scenarioType: one_off_purchase, recurring_expense, extra_savings, or unknown
- amount: a non-negative number or null
- frequency: weekly, monthly, yearly, one_time, or null
- description: a short string or null
- goalId: house_deposit, japan_holiday, emergency_fund, or null. Use null
  when the question does not name a goal.

Question: {question}
""".strip()

    try:
        response_text = _invoke_bedrock(prompt, max_tokens=250)
        response_data = _parse_json_object(response_text)
        return ParsedScenario.model_validate(response_data)
    except Exception:
        logger.warning(
            "Bedrock question parsing failed; using mock parser",
            exc_info=True,
        )
        return parse_question_mock(question)


def _generate_mock_explanation(
    customer: CustomerProfile,
    scenario: ParsedScenario,
    result: SimulationResult,
) -> str:
    description = (scenario.description or "This change").lower()
    target_impact = next(
        (
            impact
            for impact in result.goalImpacts
            if scenario.goalId and impact.goalId == scenario.goalId
        ),
        None,
    )
    if target_impact is None:
        target_impact = next(
            (
                impact
                for impact in result.goalImpacts
                if impact.monthsBefore != impact.monthsAfter
            ),
            result.goalImpacts[0] if result.goalImpacts else None,
        )

    if scenario.scenarioType == "one_off_purchase":
        impact = (
            f"The {description} would change your available balance from "
            f"${result.before.balance:,.2f} to ${result.after.balance:,.2f}."
        )
    elif scenario.scenarioType == "recurring_expense":
        impact = (
            f"The {description} would change monthly cash flow from "
            f"${result.before.monthlyCashFlow:,.2f} to "
            f"${result.after.monthlyCashFlow:,.2f}."
        )
    else:
        contribution = target_impact.monthlyContributionAfter if target_impact else 0
        goal_name = target_impact.goalName if target_impact else "financial goal"
        impact = (
            f"The {description} would raise your {goal_name} contribution to "
            f"${contribution:,.2f} per month."
        )

    timeline = ""
    if (
        target_impact
        and target_impact.monthsBefore is not None
        and target_impact.monthsAfter is not None
    ):
        difference = target_impact.monthsAfter - target_impact.monthsBefore
        if difference > 0:
            timeline = (
                f" Your {target_impact.goalName} is delayed by {difference} "
                f"month{'s' if difference != 1 else ''}."
            )
        elif difference < 0:
            timeline = (
                f" Your {target_impact.goalName} moves forward by {abs(difference)} "
                f"month{'s' if difference != -1 else ''}."
            )
        else:
            timeline = f" Your {target_impact.goalName} timeline is unchanged."

    recommendation = result.recommendation
    adjustment = recommendation.description if recommendation else ""
    if recommendation and recommendation.weeklyAmount is not None:
        adjustment += f" A ${recommendation.weeklyAmount:,.2f} weekly adjustment is suggested."

    return (
        f"{impact}{timeline} The calculated risk level is {result.riskLevel}. "
        f"{adjustment}"
    ).strip()


def generate_explanation(
    customer: CustomerProfile,
    scenario: ParsedScenario,
    result: SimulationResult,
) -> str:
    if AI_MODE != "bedrock":
        return _generate_mock_explanation(customer, scenario, result)

    prompt = f"""
Write a concise, plain-language explanation of this financial simulation.
Do not invent figures or provide regulated financial advice. Use at most
three sentences.

Customer:
{customer.model_dump_json()}

Scenario:
{scenario.model_dump_json()}

Simulation result:
{result.model_dump_json()}
""".strip()

    try:
        return _invoke_bedrock(prompt, max_tokens=220)
    except Exception:
        logger.warning(
            "Bedrock explanation generation failed; using mock explanation",
            exc_info=True,
        )
        return _generate_mock_explanation(customer, scenario, result)
