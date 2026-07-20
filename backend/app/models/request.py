from pydantic import BaseModel, Field


class SimulationRequest(BaseModel):
    customerId: str = Field(
        min_length=1,
        description="Customer identifier"
    )
    question: str = Field(
        min_length=1,
        description="Financial what-if question"
    )