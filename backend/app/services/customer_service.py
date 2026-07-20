"""Customer repository adapter for local synthetic data and DynamoDB."""

import os
from decimal import Decimal
from typing import Any

import boto3

from app.data import load_customer_profile
from app.models.customer import CustomerProfile

DATA_SOURCE = os.getenv("DATA_SOURCE", "mock")
TABLE_NAME = os.getenv("CUSTOMER_TABLE_NAME", "FutureYouCustomers")
AWS_REGION = os.getenv("AWS_REGION_NAME", "ap-southeast-2")


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
    response = table.get_item(Key={"customerId": customer_id})
    item = response.get("Item")
    if item is None:
        return None
    return CustomerProfile.model_validate(_convert_decimal(item))


def get_customer(customer_id: str) -> CustomerProfile | None:
    normalized_id = customer_id.strip().lower()
    if DATA_SOURCE == "dynamodb":
        return _get_dynamodb_customer(normalized_id)
    try:
        return load_customer_profile(normalized_id)
    except ValueError:
        return None
