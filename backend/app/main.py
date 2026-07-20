from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app.models.customer import CustomerProfile
from app.models.planning import (
    AffordabilitySummary,
    FinancialHealthScore,
    GoalAllocationRequest,
    GoalAllocationResult,
    StressTestRequest,
    StressTestResult,
)
from app.models.request import SimulationRequest
from app.models.response import SimulationResponse
from app.services.bedrock_service import (
    generate_explanation,
    parse_financial_question,
)
from app.services.customer_service import get_customer
from app.services.planning_service import (
    calculate_affordability,
    calculate_financial_health,
    optimize_goal_allocation,
    run_stress_test,
)
from app.services.simulation_service import run_simulation

app = FastAPI(title="Future You API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)


@app.get("/")
def api_home():
    return {
        "name": "Future You API",
        "status": "ok",
        "docs": "/docs",
        "health": "/health",
        "endpoints": [
            "GET /customer/{customer_id}",
            "GET /customer/{customer_id}/health-score",
            "GET /customer/{customer_id}/affordability",
            "POST /simulate",
            "POST /stress-test",
            "POST /optimize-goals",
        ],
    }


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get(
    "/customer/{customer_id}",
    response_model=CustomerProfile,
)
def customer_profile(customer_id: str) -> CustomerProfile:
    customer = get_customer(customer_id)

    if customer is None:
        raise HTTPException(
            status_code=404,
            detail="Customer not found",
        )

    return customer


@app.get(
    "/customer/{customer_id}/health-score",
    response_model=FinancialHealthScore,
)
def customer_health_score(customer_id: str) -> FinancialHealthScore:
    customer = get_customer(customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    return calculate_financial_health(customer)


@app.get(
    "/customer/{customer_id}/affordability",
    response_model=AffordabilitySummary,
)
def customer_affordability(
    customer_id: str,
    goal_id: str = Query(default="house_deposit", alias="goalId"),
) -> AffordabilitySummary:
    customer = get_customer(customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    try:
        return calculate_affordability(customer, goal_id)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.post(
    "/stress-test",
    response_model=StressTestResult,
)
def stress_test(request: StressTestRequest) -> StressTestResult:
    customer = get_customer(request.customerId)
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    return run_stress_test(
        customer,
        income_loss_months=request.incomeLossMonths,
        unexpected_expense=request.unexpectedExpense,
    )


@app.post(
    "/optimize-goals",
    response_model=GoalAllocationResult,
)
def optimize_goals(request: GoalAllocationRequest) -> GoalAllocationResult:
    customer = get_customer(request.customerId)
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    try:
        return optimize_goal_allocation(
            customer,
            priority_goal_id=request.priorityGoalId,
            target_months=request.targetMonths,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.post(
    "/simulate",
    response_model=SimulationResponse,
)
def simulate(
    request: SimulationRequest,
) -> SimulationResponse:
    customer = get_customer(request.customerId)

    if customer is None:
        raise HTTPException(
            status_code=404,
            detail="Customer not found",
        )

    scenario = parse_financial_question(request.question)

    if scenario.scenarioType == "unknown":
        raise HTTPException(
            status_code=400,
            detail="Unsupported financial scenario",
        )

    if scenario.amount is None or scenario.amount <= 0:
        raise HTTPException(
            status_code=400,
            detail="A positive financial amount is required",
        )

    result = run_simulation(
        customer=customer,
        scenario=scenario,
    )

    explanation = generate_explanation(
        customer=customer,
        scenario=scenario,
        result=result,
    )

    return SimulationResponse(
        success=True,
        customer=customer,
        scenario=scenario,
        result=result,
        explanation=explanation,
        message=f"Simulation completed for {customer.name}",
    )
