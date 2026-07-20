from pydantic import BaseModel

from app.models.customer import CustomerProfile
from app.models.scenario import ParsedScenario
from app.models.simulation import SimulationResult


class SimulationResponse(BaseModel):
    success: bool
    customer: CustomerProfile | None = None
    scenario: ParsedScenario | None = None
    result: SimulationResult | None = None
    explanation: str | None = None
    message: str | None = None
    error: str | None = None