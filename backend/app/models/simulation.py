from pydantic import BaseModel, Field


class FinancialSnapshot(BaseModel):
    balance: float
    monthlyCashFlow: float
    goalMonths: int | None = None


class Recommendation(BaseModel):
    description: str
    weeklyAmount: float | None = None


class GoalImpact(BaseModel):
    goalId: str
    goalName: str
    monthsBefore: int | None
    monthsAfter: int | None
    monthlyContributionBefore: float
    monthlyContributionAfter: float


class SimulationResult(BaseModel):
    before: FinancialSnapshot
    after: FinancialSnapshot
    beforeRiskLevel: str = "Low"
    riskLevel: str
    riskReasons: list[str] = Field(default_factory=list)
    goalImpacts: list[GoalImpact] = Field(default_factory=list)
    recommendation: Recommendation | None = None
