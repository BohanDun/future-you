from typing import Literal

from pydantic import BaseModel, Field


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
    scenarioType: ScenarioType
    amount: float | None = Field(default=None, ge=0)
    frequency: FrequencyType | None = None
    description: str | None = None