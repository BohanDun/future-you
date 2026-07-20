import os


def get_ai_mode() -> str:
    return os.getenv("AI_MODE", "bedrock").strip().lower()


AWS_REGION = os.getenv("AWS_REGION_NAME", "ap-southeast-2")
BEDROCK_MODEL_ID = os.getenv(
    "BEDROCK_MODEL_ID",
    "amazon.nova-lite-v1:0",
)
