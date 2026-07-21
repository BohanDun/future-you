from datetime import date
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class FinancialGoal(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False, str_strip_whitespace=True)

    goalId: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=80)
    target: float = Field(gt=0)
    current: float = Field(ge=0)
    monthlyContribution: float = Field(ge=0)


class Transaction(BaseModel):
    transactionId: str = Field(min_length=1)
    customerId: str = Field(min_length=1)
    date: date
    description: str = Field(min_length=1)
    category: str = Field(min_length=1)
    amount: float = Field(gt=0)
    direction: Literal["income", "expense"]


class CustomerProfile(BaseModel):
    customerId: str
    name: str
    currency: str = Field(default="NZD", min_length=3, max_length=3)

    currentBalance: float = Field(ge=0)
    monthlyIncome: float = Field(ge=0)
    monthlyExpenses: float = Field(ge=0)
    monthlySavings: float

    goals: list[FinancialGoal] = Field(default_factory=list)

    spending: dict[str, dict[str, float]] = Field(
        default_factory=dict
    )
    spendingCategories: dict[str, float] = Field(
        default_factory=dict
    )
    insights: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def monthly_savings_matches_cash_flow(self) -> Self:
        expected = round(self.monthlyIncome - self.monthlyExpenses, 2)
        if abs(self.monthlySavings - expected) > 0.01:
            raise ValueError(
                "monthlySavings must equal monthlyIncome - monthlyExpenses"
            )
        return self
