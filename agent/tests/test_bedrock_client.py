import os
from unittest.mock import patch

import pytest

from agent import bedrock_client


@pytest.mark.parametrize(
    ("variable", "value"),
    [
        ("AWS_PROFILE", "future-you"),
        ("AWS_BEARER_TOKEN_BEDROCK", "test-api-key"),
    ],
)
def test_runtime_client_preserves_boto3_credential_source(
    monkeypatch: pytest.MonkeyPatch,
    variable: str,
    value: str,
) -> None:
    monkeypatch.delenv("AWS_PROFILE", raising=False)
    monkeypatch.delenv("AWS_BEARER_TOKEN_BEDROCK", raising=False)
    monkeypatch.setenv(variable, value)
    bedrock_client._runtime_client.cache_clear()
    fake_client = object()

    with patch(
        "agent.bedrock_client.boto3.client",
        return_value=fake_client,
    ) as make_client:
        assert bedrock_client._runtime_client() is fake_client

    make_client.assert_called_once_with(
        service_name="bedrock-runtime",
        region_name=bedrock_client.AWS_REGION,
    )
    assert os.environ[variable] == value
    bedrock_client._runtime_client.cache_clear()


def test_tool_invocation_returns_content_blocks() -> None:
    fake_client = type(
        "FakeClient",
        (),
        {
            "converse": lambda self, **kwargs: {
                "output": {
                    "message": {
                        "content": [
                            {
                                "toolUse": {
                                    "name": "update_profile",
                                    "input": {"monthlyIncome": 5000},
                                }
                            }
                        ]
                    }
                }
            }
        },
    )()

    with patch("agent.bedrock_client._runtime_client", return_value=fake_client):
        content = bedrock_client.invoke_bedrock_with_tools(
            system_prompt="Plan a safe change.",
            messages=[{"role": "user", "content": [{"text": "Update income"}]}],
            tools=[{"toolSpec": {"name": "update_profile"}}],
        )

    assert content[0]["toolUse"]["name"] == "update_profile"
