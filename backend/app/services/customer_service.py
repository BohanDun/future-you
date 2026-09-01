"""Customer repository adapter for local synthetic data and DynamoDB."""

import json
import os
from decimal import Decimal
from pathlib import Path
from typing import Any

import boto3

from app.data import load_customer_profile
from app.financial_tools import generate_dashboard_insights
from app.models.customer import CustomerProfile

DATA_SOURCE = os.getenv("DATA_SOURCE", "mock").strip().lower()
TABLE_NAME = os.getenv(
    "USER_PROFILE_TABLE_NAME",
    os.getenv("CUSTOMER_TABLE_NAME", "future-you-users"),
)
AWS_REGION = os.getenv("AWS_REGION_NAME", "ap-southeast-2")
DEFAULT_MOCK_STATE_DIR = Path(__file__).resolve().parents[2] / ".local" / "mock-customers"


def _refresh_dashboard_insights(profile: CustomerProfile) -> CustomerProfile:
    if not profile.spendingCategories:
        return profile
    return profile.model_copy(update={
        "insights": generate_dashboard_insights(
            spending_history=profile.spending,
            latest_categories=profile.spendingCategories,
            monthly_income=profile.monthlyIncome,
            monthly_savings=profile.monthlySavings,
        )
    })


def _convert_decimal(value: Any) -> Any:
    if isinstance(value, Decimal):
        if value % 1 == 0:
            return int(value)
        return float(value)
    if isinstance(value, list):
        return [_convert_decimal(item) for item in value]
    if isinstance(value, dict):
        return {key: _convert_decimal(item) for key, item in value.items()}
    return value


def _get_dynamodb_customer(customer_id: str) -> CustomerProfile | None:
    dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
    table = dynamodb.Table(TABLE_NAME)
    response = table.get_item(Key={"userId": customer_id})
    item = response.get("Item")
    if item is None:
        return None
    profile = CustomerProfile.model_validate(_convert_decimal(item))
    return _refresh_dashboard_insights(profile)


def _to_dynamodb(value: Any) -> Any:
    if isinstance(value, float):
        return Decimal(str(value))
    if isinstance(value, list):
        return [_to_dynamodb(item) for item in value]
    if isinstance(value, dict):
        return {key: _to_dynamodb(item) for key, item in value.items()}
    return value


def _mock_state_dir() -> Path:
    configured = os.getenv("FUTURE_YOU_MOCK_STATE_DIR", "").strip()
    return Path(configured).expanduser() if configured else DEFAULT_MOCK_STATE_DIR


def _mock_profile_path(customer_id: str) -> Path:
    # load_customer_profile performs the same identifier validation for fixture reads.
    allowed = "abcdefghijklmnopqrstuvwxyz0123456789_-"
    if not customer_id or any(char not in allowed for char in customer_id):
        raise ValueError("Invalid customer identifier")
    return _mock_state_dir() / f"{customer_id}.json"


def _get_mock_customer(customer_id: str) -> CustomerProfile | None:
    path = _mock_profile_path(customer_id)
    if path.exists():
        with path.open(encoding="utf-8") as stream:
            return _refresh_dashboard_insights(CustomerProfile.model_validate(json.load(stream)))
    return load_customer_profile(customer_id)


def _save_mock_customer(profile: CustomerProfile) -> CustomerProfile:
    state_dir = _mock_state_dir()
    state_dir.mkdir(parents=True, exist_ok=True)
    destination = _mock_profile_path(profile.customerId.strip().lower())
    temporary = destination.with_suffix(".tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(profile.model_dump(mode="json"), stream, indent=2)
        stream.write("\n")
    temporary.replace(destination)
    return profile


def save_customer_profile(
    profile: CustomerProfile,
    *,
    email: str | None = None,
) -> CustomerProfile:
    if DATA_SOURCE == "mock":
        return _save_mock_customer(profile)
    if DATA_SOURCE != "dynamodb":
        raise RuntimeError(
            f"Unsupported DATA_SOURCE={DATA_SOURCE!r}. Use 'mock' or 'dynamodb'."
        )

    dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
    table = dynamodb.Table(TABLE_NAME)
    item = profile.model_dump(mode="json")
    item.update(
        {
            "userId": profile.customerId,
            "onboardingComplete": True,
        }
    )
    if email:
        item["email"] = email
    table.put_item(Item=_to_dynamodb(item))
    return profile


def get_customer(customer_id: str) -> CustomerProfile | None:
    normalized_id = customer_id.strip().lower()
    if DATA_SOURCE == "dynamodb":
        return _get_dynamodb_customer(normalized_id)
    if DATA_SOURCE != "mock":
        raise RuntimeError(
            f"Unsupported DATA_SOURCE={DATA_SOURCE!r}. Use 'mock' or 'dynamodb'."
        )
    try:
        return _get_mock_customer(normalized_id)
    except ValueError:
        return None
