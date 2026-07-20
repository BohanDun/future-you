import os

os.environ["AI_MODE"] = "mock"

import pytest

from agent.tests.fixtures.virtual_users import VIRTUAL_USERS, build_jordan, build_riley, build_sam
from app.data import load_customer_profile
from app.models.customer import CustomerProfile


@pytest.fixture
def alex() -> CustomerProfile:
    customer = load_customer_profile("alex")
    assert customer is not None
    return customer


@pytest.fixture
def sam() -> CustomerProfile:
    return build_sam()


@pytest.fixture
def jordan() -> CustomerProfile:
    return build_jordan()


@pytest.fixture
def riley() -> CustomerProfile:
    return build_riley()


@pytest.fixture(params=list(VIRTUAL_USERS.keys()))
def virtual_user(request: pytest.FixtureRequest) -> CustomerProfile:
    return VIRTUAL_USERS[request.param]
