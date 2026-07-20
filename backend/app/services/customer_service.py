import os
from decimal import Decimal
from typing import Any

import boto3

from app.models.customer import CustomerProfile


MOCK_CUSTOMERS: dict[str, CustomerProfile] = {
    "alex": CustomerProfile(
        customerId="alex",
        name="Alex",
        currentBalance=8000,
        monthlyIncome=5200,
        monthlyExpenses=3850,
        monthlySavings=1350,
        goals=[
            {
                "goalId": "house_deposit",
                "name": "House Deposit",
                "target": 20000,
                "current": 8000,
                "monthlyContribution": 700,
            },
            {
                "goalId": "japan_holiday",
                "name": "Japan Holiday",
                "target": 3000,
                "current": 1200,
                "monthlyContribution": 300,
            },
            {
                "goalId": "emergency_fund",
                "name": "Emergency Fund",
                "target": 5000,
                "current": 3500,
                "monthlyContribution": 350,
            },
        ],
        spending={
            "dining": {
                "April": 310,
                "May": 356,
                "June": 420,
            }
        },
    )
}


DATA_SOURCE = os.getenv("DATA_SOURCE", "mock")
TABLE_NAME = os.getenv(
    "CUSTOMER_TABLE_NAME",
    "FutureYouCustomers",
)
AWS_REGION = os.getenv(
    "AWS_REGION_NAME",
    "ap-southeast-2",
)


def _convert_decimal(value: Any) -> Any:
    if isinstance(value, Decimal):
        if value % 1 == 0:
            return int(value)
        return float(value)

    if isinstance(value, list):
        return [_convert_decimal(item) for item in value]

    if isinstance(value, dict):
        return {
            key: _convert_decimal(item)
            for key, item in value.items()
        }

    return value


def _get_mock_customer(
    customer_id: str,
) -> CustomerProfile | None:
    return MOCK_CUSTOMERS.get(customer_id)


def _get_dynamodb_customer(
    customer_id: str,
) -> CustomerProfile | None:
    dynamodb = boto3.resource(
        "dynamodb",
        region_name=AWS_REGION,
    )

    table = dynamodb.Table(TABLE_NAME)

    response = table.get_item(
        Key={"customerId": customer_id}
    )

    item = response.get("Item")

    if item is None:
        return None

    converted_item = _convert_decimal(item)

    return CustomerProfile.model_validate(converted_item)


def get_customer(
    customer_id: str,
) -> CustomerProfile | None:
    normalized_id = customer_id.strip().lower()

    if DATA_SOURCE == "dynamodb":
        return _get_dynamodb_customer(normalized_id)

    return _get_mock_customer(normalized_id)
