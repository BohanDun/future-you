from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.models.customer import CustomerProfile
from app.models.request import SimulationRequest
from app.models.response import SimulationResponse
from app.services.bedrock_service import (
    generate_explanation,
    parse_financial_question,
)
from app.services.customer_service import get_customer
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
