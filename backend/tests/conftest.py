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
