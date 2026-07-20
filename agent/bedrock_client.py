import logging
import os
from functools import lru_cache

import boto3

from agent.config import AWS_REGION, BEDROCK_MODEL_ID

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _runtime_client():
    try:
        return boto3.client(
            service_name="bedrock-runtime",
            region_name=AWS_REGION,
        )
    except Exception as exc:  # pragma: no cover - depends on AWS environment
        raise RuntimeError(
            "Unable to initialize the Bedrock runtime client. Configure AWS credentials "
            "for the backend environment (for example via AWS_ACCESS_KEY_ID / "
            "AWS_SECRET_ACCESS_KEY or an AWS profile), or set AI_MODE to mock. "
            f"Original error: {exc}"
        ) from exc


def invoke_bedrock(
    *,
    system_prompt: str,
    user_prompt: str,
    max_tokens: int,
    temperature: float = 0.1,
) -> str:
    try:
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
    except Exception as exc:
        raise RuntimeError(f"Bedrock converse call failed. Original error: {exc}") from exc

    content = response["output"]["message"]["content"]
    text_parts = [
        block["text"]
        for block in content
        if "text" in block
    ]

    if not text_parts:
        raise ValueError("Bedrock returned no text content")

    return "".join(text_parts).strip()
