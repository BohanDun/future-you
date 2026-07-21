from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

RiskLevel = Literal["Low", "Medium", "High"]


class FinancialSnapshot(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)

    balance: float
    monthlyCashFlow: float
    goalMonths: int | None = Field(default=None, ge=0)


class Recommendation(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)

    description: str
    weeklyAmount: float | None = Field(default=None, ge=0)


class GoalImpact(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)

    goalId: str
    goalName: str
    monthsBefore: int | None = Field(ge=0)
    monthsAfter: int | None = Field(ge=0)
    monthlyContributionBefore: float = Field(ge=0)
    monthlyContributionAfter: float = Field(ge=0)
    currentAtEvent: float | None = Field(default=None, ge=0)


class SimulationResult(BaseModel):
    before: FinancialSnapshot
    after: FinancialSnapshot
    beforeRiskLevel: RiskLevel = "Low"
    riskLevel: RiskLevel
    riskReasons: list[str] = Field(default_factory=list)
    goalImpacts: list[GoalImpact] = Field(default_factory=list)
    recommendation: Recommendation | None = None
    horizonMonths: int = Field(default=0, ge=0, le=600)
    atEventBefore: FinancialSnapshot | None = None
    goalContributionsByEvent: float = Field(default=0, ge=0)
    fundedFromGoal: float = Field(default=0, ge=0)
    fundedFromBalance: float = Field(default=0, ge=0)
    eventRiskLevel: RiskLevel | None = None
    minimumProjectedBalance: float | None = None
