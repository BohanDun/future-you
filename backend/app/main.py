from agent import (
    OFF_TOPIC_RESPONSE,
    SAFETY_SUPPORT_RESPONSE,
    answer_freeform_question,
    can_run_simulation,
    generate_explanation,
    plan_profile_changes,
    route_advice_question,
)
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.financial_tools import generate_dashboard_insights
from app.models.agent_action import (
    ApplyAgentProposalRequest,
    ManageAgentRequest,
    ManageAgentResponse,
)
from app.models.customer import CustomerProfile, FinancialGoal
from app.models.request import SimulationRequest, SpendingCategoriesInput, UserProfileInput
from app.models.response import SimulationResponse
from app.models.scenario import ParsedScenario
from app.services.agent_action_service import apply_agent_operations
from app.services.auth_service import AUTH_MODE, CurrentUser
from app.services.customer_service import get_customer, save_customer_profile
from app.services.proposal_service import ProposalTokenError, verify_proposal_token
from app.services.simulation_service import run_simulation

app = FastAPI(title="Future You API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get(
    "/customer/{customer_id}",
    response_model=CustomerProfile,
)
def customer_profile(
    customer_id: str,
    user: CurrentUser,
) -> CustomerProfile:
    if AUTH_MODE == "cognito" and customer_id != user.user_id:
        raise HTTPException(status_code=403, detail="Cannot access another user's profile")
    customer = get_customer(customer_id)

    if customer is None:
        raise HTTPException(
            status_code=404,
            detail="Customer not found",
        )

    return customer


@app.get("/me/profile", response_model=CustomerProfile)
def current_user_profile(
    user: CurrentUser,
) -> CustomerProfile:
    customer = get_customer(user.user_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="PROFILE_NOT_FOUND")
    return customer


@app.put("/me/profile", response_model=CustomerProfile)
def update_current_user_profile(
    profile_input: UserProfileInput,
    user: CurrentUser,
) -> CustomerProfile:
    profile = profile_input.to_customer_profile(user.user_id)
    try:
        return save_customer_profile(profile, email=user.email)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/me/goals", response_model=CustomerProfile, status_code=201)
def add_current_user_goal(
    goal: FinancialGoal,
    user: CurrentUser,
) -> CustomerProfile:
    profile = get_customer(user.user_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="PROFILE_NOT_FOUND")
    if len(profile.goals) >= 10:
        raise HTTPException(status_code=409, detail="A profile can have at most 10 goals")
    if any(existing.goalId == goal.goalId for existing in profile.goals):
        raise HTTPException(status_code=409, detail="A goal with this ID already exists")
    if any(existing.name.casefold() == goal.name.casefold() for existing in profile.goals):
        raise HTTPException(status_code=409, detail="A goal with this name already exists")

    profile.goals.append(goal)
    try:
        return save_customer_profile(profile, email=user.email)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.delete("/me/goals/{goal_id}", response_model=CustomerProfile)
def delete_current_user_goal(
    goal_id: str,
    user: CurrentUser,
) -> CustomerProfile:
    profile = get_customer(user.user_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="PROFILE_NOT_FOUND")

    matching_goal = next((goal for goal in profile.goals if goal.goalId == goal_id), None)
    if matching_goal is None:
        raise HTTPException(status_code=404, detail="Goal not found")

    profile.goals = [goal for goal in profile.goals if goal.goalId != goal_id]
    try:
        return save_customer_profile(profile, email=user.email)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.put("/me/spending-categories", response_model=CustomerProfile)
def update_current_user_spending_categories(
    request: SpendingCategoriesInput,
    user: CurrentUser,
) -> CustomerProfile:
    profile = get_customer(user.user_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="PROFILE_NOT_FOUND")

    profile.spendingCategories = request.categories
    profile.monthlyExpenses = round(sum(request.categories.values()), 2)
    profile.monthlySavings = round(profile.monthlyIncome - profile.monthlyExpenses, 2)
    profile.insights = generate_dashboard_insights(
        spending_history=profile.spending,
        latest_categories=request.categories,
        monthly_income=profile.monthlyIncome,
        monthly_savings=profile.monthlySavings,
    )
    try:
        return save_customer_profile(profile, email=user.email)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/agent/manage", response_model=ManageAgentResponse)
def manage_agent(
    request: ManageAgentRequest,
    user: CurrentUser,
) -> ManageAgentResponse:
    profile = get_customer(user.user_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="PROFILE_NOT_FOUND")
    return plan_profile_changes(profile, request.message, request.history)


@app.post("/agent/proposals/apply", response_model=CustomerProfile)
def apply_agent_proposal(
    request: ApplyAgentProposalRequest,
    user: CurrentUser,
) -> CustomerProfile:
    profile = get_customer(user.user_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="PROFILE_NOT_FOUND")
    try:
        operations = verify_proposal_token(request.proposalToken, profile)
        updated = apply_agent_operations(profile, operations)
        return save_customer_profile(updated, email=user.email)
    except ProposalTokenError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post(
    "/simulate",
    response_model=SimulationResponse,
)
def simulate(
    request: SimulationRequest,
    user: CurrentUser,
) -> SimulationResponse:
    customer_id = (
        user.user_id
        if AUTH_MODE == "cognito"
        else (request.customerId or user.user_id)
    )
    customer = get_customer(customer_id)

    if customer is None:
        raise HTTPException(
            status_code=404,
            detail="Customer not found",
        )

    route = route_advice_question(customer, request.question, request.history)

    if route.kind in {"off_topic", "safety_support"}:
        return SimulationResponse(
            success=True,
            customer=customer,
            explanation=(
                SAFETY_SUPPORT_RESPONSE
                if route.kind == "safety_support"
                else OFF_TOPIC_RESPONSE
            ),
            message=f"Guidance for {customer.name}",
        )

    scenario = route.scenario or ParsedScenario(
        scenarioType="unknown",
        amount=None,
    )

    if not can_run_simulation(scenario):
        explanation = answer_freeform_question(
            customer=customer,
            question=request.question,
            history=request.history,
        )
        return SimulationResponse(
            success=True,
            customer=customer,
            explanation=explanation,
            message=f"Guidance for {customer.name}",
        )

    result = run_simulation(
        customer=customer,
        scenario=scenario,
    )

    explanation = generate_explanation(
        customer=customer,
        scenario=scenario,
        result=result,
        question=request.question,
    )

    return SimulationResponse(
        success=True,
        customer=customer,
        scenario=scenario,
        result=result,
        explanation=explanation,
        message=f"Simulation completed for {customer.name}",
    )
