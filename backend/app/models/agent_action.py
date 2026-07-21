from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ConversationMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=2000)


class GoalValues(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=80)
    target: float = Field(gt=0)
    current: float = Field(default=0, ge=0)
    monthlyContribution: float = Field(ge=0)


class CreateGoalOperation(BaseModel):
    """Create one goal. This is the only supported create operation."""

    model_config = ConfigDict(extra="forbid")

    operation: Literal["create"]
    resource: Literal["goal"]
    values: GoalValues


class SetProfileOperation(BaseModel):
    """Set one editable profile field to an explicit value."""

    model_config = ConfigDict(extra="forbid")

    operation: Literal["set"]
    resource: Literal["profile"]
    field: Literal["currentBalance", "monthlyIncome", "monthlyExpenses"]
    value: float = Field(ge=0)


class SetGoalOperation(BaseModel):
    """Set one field on a goal that belongs to the authenticated customer."""

    model_config = ConfigDict(extra="forbid")

    operation: Literal["set"]
    resource: Literal["goal"]
    resourceId: str = Field(min_length=1, max_length=100)
    field: Literal["name", "target", "current", "monthlyContribution"]
    value: str | float

    @model_validator(mode="after")
    def validate_value_for_field(self):
        if self.field == "name":
            if not isinstance(self.value, str) or not self.value.strip():
                raise ValueError("A goal name must be a non-empty string")
            if len(self.value.strip()) > 80:
                raise ValueError("A goal name can have at most 80 characters")
            return self
        if isinstance(self.value, bool) or not isinstance(self.value, (int, float)):
            raise ValueError(f"{self.field} must be a number")
        if self.field == "target" and self.value <= 0:
            raise ValueError("A goal target must be greater than zero")
        if self.value < 0:
            raise ValueError(f"{self.field} cannot be negative")
        return self


AgentOperation = Annotated[
    CreateGoalOperation | SetProfileOperation | SetGoalOperation,
    Field(),
]


class ManageAgentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str = Field(min_length=1, max_length=2000)
    history: list[ConversationMessage] = Field(default_factory=list, max_length=20)


class ApplyAgentProposalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    proposalToken: str = Field(min_length=20, max_length=20_000)


class ChangePreview(BaseModel):
    label: str
    before: str | None = None
    after: str


class ClarificationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    missingFields: list[str] = Field(min_length=1, max_length=8)
    question: str = Field(min_length=1, max_length=500)


class ManageAgentResponse(BaseModel):
    message: str
    operations: list[AgentOperation] = Field(default_factory=list)
    preview: list[ChangePreview] = Field(default_factory=list)
    proposalToken: str | None = None
    clarification: ClarificationRequest | None = None
