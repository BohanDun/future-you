"""Quick Bedrock Converse smoke test using boto3's credential chain."""

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from agent.config import AWS_REGION, BEDROCK_MODEL_ID


def main() -> None:
    try:
        client = boto3.client(
            service_name="bedrock-runtime",
            region_name=AWS_REGION,
        )
        response = client.converse(
            modelId=BEDROCK_MODEL_ID,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "text": "Explain what an AI agent is in simple English.",
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
        raise SystemExit(1) from error
    except BotoCoreError as error:
        print("Authentication or connection error:", error)
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
