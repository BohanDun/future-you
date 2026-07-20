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
    description = scenario.description or "this change"
    return (
        f"For {customer.name}, {description} changes the balance from "
        f"${result.before.balance:,.2f} to ${result.after.balance:,.2f}. "
        f"The estimated risk level is {result.riskLevel}."
    )


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
