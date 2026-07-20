from pydantic import BaseModel, Field, model_validator


class AffordabilitySummary(BaseModel):
    customerId: str
    goalId: str
    goalName: str
    availableBalance: float
    reserveMonths: float
    lowRiskLimit: float
    mediumRiskLimit: float
    highRiskStartsAt: float | None = None
    lowRiskBoundaryReasons: list[str] = Field(default_factory=list)
    mediumRiskBoundaryReasons: list[str] = Field(default_factory=list)


class FinancialHealthComponent(BaseModel):
    key: str
    label: str
    score: float
    maxScore: float
    summary: str


class FinancialHealthScore(BaseModel):
    customerId: str
    score: int = Field(ge=0, le=100)
    status: str
    savingsRatePercent: float
    reserveMonths: float
    goalProgressPercent: float
    components: list[FinancialHealthComponent] = Field(default_factory=list)
    nextBestAction: str


class StressTestRequest(BaseModel):
    customerId: str = Field(min_length=1)
    incomeLossMonths: int = Field(default=0, ge=0, le=12)
    unexpectedExpense: float = Field(default=0, ge=0)

    @model_validator(mode="after")
    def includes_a_shock(self):
        if self.incomeLossMonths == 0 and self.unexpectedExpense == 0:
            raise ValueError("At least one financial shock is required")
        return self


class StressGoalImpact(BaseModel):
    goalId: str
    goalName: str
    monthsBefore: int | None
    monthsAfter: int | None


class StressTestResult(BaseModel):
    customerId: str
    balanceBefore: float
    balanceAfter: float
    runwayMonthsBefore: float
    runwayMonthsAfter: float
    monthlyCashFlowDuringShock: float
    riskLevel: str
    riskReasons: list[str] = Field(default_factory=list)
    goalImpacts: list[StressGoalImpact] = Field(default_factory=list)
    recommendation: str


class GoalAllocationRequest(BaseModel):
    customerId: str = Field(min_length=1)
    priorityGoalId: str = Field(min_length=1)
    targetMonths: int = Field(ge=1, le=120)


class GoalAllocation(BaseModel):
    goalId: str
    goalName: str
    monthlyContributionBefore: float
    monthlyContributionAfter: float
    monthsBefore: int | None
    monthsAfter: int | None


class GoalAllocationResult(BaseModel):
    customerId: str
    priorityGoalId: str
    requestedMonths: int
    earliestPossibleMonths: int | None
    feasible: bool
    monthlySavingsAvailable: float
    allocations: list[GoalAllocation]
    summary: str
