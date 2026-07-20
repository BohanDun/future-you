"""Quick Bedrock Converse smoke test. Requires AWS_BEARER_TOKEN_BEDROCK in the environment."""

import os

import boto3
from botocore.exceptions import ClientError

from agent.config import AWS_REGION, BEDROCK_MODEL_ID


def main() -> None:
    if not os.getenv("AWS_BEARER_TOKEN_BEDROCK"):
        raise SystemExit(
            "Set AWS_BEARER_TOKEN_BEDROCK first, e.g.\n"
            "  export AWS_BEARER_TOKEN_BEDROCK='your-api-key'"
        )

    for key in (
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_SESSION_TOKEN",
        "AWS_PROFILE",
    ):
        os.environ.pop(key, None)

    client = boto3.client(
        service_name="bedrock-runtime",
        region_name=AWS_REGION,
    )

    try:
        response = client.converse(
            modelId=BEDROCK_MODEL_ID,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "text": "请用简单的语言解释什么是 AI agent。",
                        }
                    ],
                }
            ],
            inferenceConfig={
                "maxTokens": 500,
                "temperature": 0.2,
                "topP": 0.9,
            },
        )

        answer = response["output"]["message"]["content"][0]["text"]
        print(answer)

        if "usage" in response:
            print("\nToken usage:", response["usage"])

    except ClientError as error:
        error_info = error.response.get("Error", {})
        print("Error code:", error_info.get("Code"))
        print("Error message:", error_info.get("Message"))


if __name__ == "__main__":
    main()
