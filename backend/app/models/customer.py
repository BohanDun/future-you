from pydantic import BaseModel, Field


class FinancialGoal(BaseModel):
    goalId: str
    name: str
    target: float = Field(ge=0)
    current: float = Field(ge=0)
    monthlyContribution: float = Field(ge=0)


class CustomerProfile(BaseModel):
    customerId: str
    name: str

    currentBalance: float
    monthlyIncome: float
    monthlyExpenses: float
    monthlySavings: float

    goals: list[FinancialGoal] = Field(default_factory=list)

    spending: dict[str, dict[str, float]] = Field(
        default_factory=dict
    )