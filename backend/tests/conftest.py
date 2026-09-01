import os

os.environ["AI_MODE"] = "mock"
os.environ["AGENT_PROPOSAL_SIGNING_KEY"] = "test-only-proposal-signing-key-32-chars"

import pytest

from app.data import load_customer_profile
from app.models.customer import CustomerProfile


@pytest.fixture
def alex() -> CustomerProfile:
    customer = load_customer_profile("alex")
    assert customer is not None
    return customer


@pytest.fixture(autouse=True)
def isolate_mock_state(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    """Keep API tests independent from profiles saved by the local demo."""
    monkeypatch.setenv("FUTURE_YOU_MOCK_STATE_DIR", str(tmp_path / "mock-customers"))
