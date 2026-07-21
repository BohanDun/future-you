from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, model_validator

from app.models.scenario import ParsedScenario


class AdviceRoute(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["simulation", "financial_advice", "off_topic", "safety_support"]
    scenario: ParsedScenario | None = None

    @model_validator(mode="after")
    def simulation_has_scenario(self) -> Self:
        if self.kind == "simulation" and self.scenario is None:
            raise ValueError("A simulation route requires a scenario")
        if self.kind != "simulation" and self.scenario is not None:
            raise ValueError("Only a simulation route can contain a scenario")
        return self
