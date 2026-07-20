import logging
import os
from functools import lru_cache

import boto3

from agent.config import AWS_REGION, BEDROCK_MODEL_ID

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _runtime_client():
    if not os.getenv("AWS_BEARER_TOKEN_BEDROCK"):
        raise RuntimeError(
            "AWS_BEARER_TOKEN_BEDROCK is not set. "
            "Export your Bedrock API key before starting the backend."
        )

    return boto3.client(
        service_name="bedrock-runtime",
        region_name=AWS_REGION,
    )


def invoke_bedrock(
    *,
    system_prompt: str,
    user_prompt: str,
    max_tokens: int,
    temperature: float = 0.1,
) -> str:
    response = _runtime_client().converse(
        modelId=BEDROCK_MODEL_ID,
        system=[{"text": system_prompt}],
        messages=[
            {
                "role": "user",
                "content": [{"text": user_prompt}],
            }
        ],
        inferenceConfig={
            "maxTokens": max_tokens,
            "temperature": temperature,
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
