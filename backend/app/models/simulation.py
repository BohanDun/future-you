from pydantic import BaseModel


class FinancialSnapshot(BaseModel):
    balance: float
    monthlyCashFlow: float
    goalMonths: int | None = None


class Recommendation(BaseModel):
    description: str
    weeklyAmount: float | None = None


class SimulationResult(BaseModel):
    before: FinancialSnapshot
    after: FinancialSnapshot
    riskLevel: str
    recommendation: Recommendation | None = None