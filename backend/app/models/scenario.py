from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

ScenarioType = Literal[
    "one_off_purchase",
    "recurring_expense",
    "extra_savings",
    "unknown",
]

FrequencyType = Literal[
    "weekly",
    "monthly",
    "yearly",
    "one_time",
]


class ParsedScenario(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    scenarioType: ScenarioType
    amount: float | None = Field(default=None, ge=0)
    frequency: FrequencyType | None = None
    description: str | None = Field(default=None, max_length=120)
    goalId: str | None = Field(default=None, max_length=100)
    horizonMonths: int = Field(default=0, ge=0, le=600)
    timingLabel: str | None = Field(default=None, max_length=80)

    @model_validator(mode="after")
    def frequency_matches_scenario(self):
        recurring = {"weekly", "monthly", "yearly", None}
        if self.scenarioType == "one_off_purchase" and self.frequency not in {
            "one_time",
            None,
        }:
            raise ValueError("A one-off purchase must use one_time frequency")
        if self.scenarioType in {"recurring_expense", "extra_savings"}:
            if self.frequency not in recurring:
                raise ValueError("A recurring scenario must use a recurring frequency")
        return self
