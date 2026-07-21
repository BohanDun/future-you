"""Customer repository adapter for local synthetic data and DynamoDB."""

import os
from decimal import Decimal
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


def save_customer_profile(
    profile: CustomerProfile,
    *,
    email: str | None = None,
) -> CustomerProfile:
    if DATA_SOURCE != "dynamodb":
        raise RuntimeError("Profile saving requires DATA_SOURCE=dynamodb")

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
    try:
        return load_customer_profile(normalized_id)
    except ValueError:
        return None
