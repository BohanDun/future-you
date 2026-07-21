import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.agent_action import ConversationMessage
from app.models.customer import CustomerProfile, FinancialGoal


class SimulationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    customerId: str | None = Field(
        default=None,
        min_length=1,
        description="Demo-mode customer identifier; authenticated requests use the JWT subject",
    )
    question: str = Field(
        min_length=1,
        max_length=2000,
        description="Financial what-if question"
    )
    history: list[ConversationMessage] = Field(default_factory=list, max_length=20)


class UserProfileInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=80)
    currency: str = Field(default="NZD", min_length=3, max_length=3)
    currentBalance: float = Field(ge=0)
    monthlyIncome: float = Field(ge=0)
    monthlyExpenses: float = Field(ge=0)
    goals: list[FinancialGoal] = Field(default_factory=list, max_length=10)

    def to_customer_profile(self, customer_id: str) -> CustomerProfile:
        return CustomerProfile(
            customerId=customer_id,
            name=self.name.strip(),
            currency=self.currency.upper(),
            currentBalance=self.currentBalance,
            monthlyIncome=self.monthlyIncome,
            monthlyExpenses=self.monthlyExpenses,
            monthlySavings=round(self.monthlyIncome - self.monthlyExpenses, 2),
            goals=self.goals,
        )


class SpendingCategoriesInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    categories: dict[str, float] = Field(max_length=12)

    @field_validator("categories")
    @classmethod
    def validate_categories(cls, categories: dict[str, float]) -> dict[str, float]:
        normalized: dict[str, float] = {}
        seen_names: set[str] = set()
        for raw_name, amount in categories.items():
            name = re.sub(r"\s+", " ", raw_name.strip())
            if not name or len(name) > 40:
                raise ValueError("Category names must contain 1 to 40 characters")
            comparison_name = name.casefold()
            if comparison_name in seen_names:
                raise ValueError("Category names must be unique")
            if amount < 0:
                raise ValueError(f"{name} spending cannot be negative")
            seen_names.add(comparison_name)
            normalized[name] = round(amount, 2)
        return normalized
