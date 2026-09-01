import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.agent_action import SetProfileOperation
from app.services.proposal_service import create_proposal_token

client = TestClient(app)


def test_customer_endpoint_returns_person_two_data() -> None:
    response = client.get("/customer/alex")

    assert response.status_code == 200
    body = response.json()
    assert body["monthlySavings"] == 1350
    assert body["spendingCategories"]["housing"] == 1800
    assert len(body["insights"]) == 3


def test_me_profile_uses_authenticated_demo_identity() -> None:
    response = client.get("/me/profile")

    assert response.status_code == 200
    assert response.json()["customerId"] == "alex"


def test_simulate_can_use_authenticated_identity_without_customer_id() -> None:
    response = client.post(
        "/simulate",
        json={"question": "What happens if I buy a $2,000 laptop?"},
    )

    assert response.status_code == 200
    assert response.json()["customer"]["customerId"] == "alex"


def test_simulate_timing_follow_up_keeps_the_previous_scenario() -> None:
    response = client.post(
        "/simulate",
        json={
            "question": "What about next month?",
            "history": [
                {
                    "role": "user",
                    "content": "What happens if I buy a $2,000 laptop?",
                },
                {
                    "role": "assistant",
                    "content": "Buying it today would leave you with $6,000.",
                },
            ],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["scenario"]["amount"] == 2000
    assert body["scenario"]["description"] == "Laptop"
    assert body["scenario"]["horizonMonths"] == 1
    assert body["result"] is not None
    assert body["result"]["atEventBefore"] is not None


def test_simulate_months_later_follow_up_returns_a_dashboard() -> None:
    response = client.post(
        "/simulate",
        json={
            "question": "What about 2 months later?",
            "history": [
                {
                    "role": "user",
                    "content": "What happens if I buy a $2,000 laptop?",
                },
                {
                    "role": "assistant",
                    "content": "Buying it today would leave you with $6,000.",
                },
            ],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["scenario"]["amount"] == 2000
    assert body["scenario"]["horizonMonths"] == 2
    assert body["scenario"]["timingLabel"] == "2 months later"
    assert body["result"] is not None
    assert body["result"]["atEventBefore"] is not None
    assert "right now" not in body["explanation"].lower()


def test_non_financial_question_returns_deterministic_redirect() -> None:
    response = client.post(
        "/simulate",
        json={"question": "How do I cook dinner?"},
    )

    assert response.status_code == 200
    assert "financial planning and money questions" in response.json()["explanation"]
    assert "988" not in response.json()["explanation"]


def test_simulate_rejects_oversized_questions() -> None:
    response = client.post("/simulate", json={"question": "x" * 2001})

    assert response.status_code == 422


def test_safety_language_uses_dedicated_support_route() -> None:
    response = client.post(
        "/simulate",
        json={"question": "I want to hurt myself."},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["result"] is None
    assert "immediate safety" in body["explanation"]
    assert "financial planning right now" in body["explanation"]


@pytest.mark.parametrize(
    "question",
    [
        "Should I get a new laptop?",
        "What if my groceries go up by $50 per week?",
        "What if my utilities increase by $30 a month?",
    ],
)
def test_natural_financial_scenarios_are_not_rejected(question: str) -> None:
    response = client.post("/simulate", json={"question": question})

    assert response.status_code == 200
    assert response.json()["scenario"]["scenarioType"] != "unknown"


def test_onboarding_profile_is_derived_from_authenticated_user(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.main.save_customer_profile",
        lambda profile, email=None: profile,
    )
    response = client.put(
        "/me/profile",
        json={
            "name": "Taylor",
            "currency": "nzd",
            "currentBalance": 2500,
            "monthlyIncome": 4800,
            "monthlyExpenses": 3500,
            "goals": [
                {
                    "goalId": "emergency_fund",
                    "name": "Emergency Fund",
                    "target": 5000,
                    "current": 1000,
                    "monthlyContribution": 300,
                }
            ],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["customerId"] == "alex"
    assert body["currency"] == "NZD"
    assert body["monthlySavings"] == 1300


def test_onboarding_allows_negative_monthly_cash_flow(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.main.save_customer_profile",
        lambda profile, email=None: profile,
    )

    response = client.put(
        "/me/profile",
        json={
            "name": "Taylor",
            "currency": "NZD",
            "currentBalance": 500,
            "monthlyIncome": 3000,
            "monthlyExpenses": 3500,
            "goals": [{
                "goalId": "buffer",
                "name": "Buffer",
                "target": 1000,
                "current": 0,
                "monthlyContribution": 0,
            }],
        },
    )

    assert response.status_code == 200
    assert response.json()["monthlySavings"] == -500


def test_goal_target_must_be_positive() -> None:
    response = client.post(
        "/me/goals",
        json={
            "goalId": "invalid",
            "name": "Invalid",
            "target": 0,
            "current": 0,
            "monthlyContribution": 0,
        },
    )

    assert response.status_code == 422


def test_add_goal_appends_to_authenticated_profile(monkeypatch, alex) -> None:
    monkeypatch.setattr("app.main.get_customer", lambda customer_id: alex.model_copy(deep=True))
    monkeypatch.setattr(
        "app.main.save_customer_profile",
        lambda profile, email=None: profile,
    )

    response = client.post(
        "/me/goals",
        json={
            "goalId": "new_car",
            "name": "New Car",
            "target": 12000,
            "current": 1000,
            "monthlyContribution": 400,
        },
    )

    assert response.status_code == 201
    assert response.json()["goals"][-1] == {
        "goalId": "new_car",
        "name": "New Car",
        "target": 12000.0,
        "current": 1000.0,
        "monthlyContribution": 400.0,
    }


def test_delete_goal_removes_it_from_authenticated_profile(monkeypatch, alex) -> None:
    saved_profiles = []
    monkeypatch.setattr("app.main.get_customer", lambda customer_id: alex.model_copy(deep=True))
    monkeypatch.setattr(
        "app.main.save_customer_profile",
        lambda profile, email=None: saved_profiles.append(profile) or profile,
    )
    goal = alex.goals[0]

    response = client.delete(f"/me/goals/{goal.goalId}")

    assert response.status_code == 200
    assert all(item["goalId"] != goal.goalId for item in response.json()["goals"])
    assert len(saved_profiles) == 1


def test_delete_goal_returns_not_found_for_unknown_goal(monkeypatch, alex) -> None:
    monkeypatch.setattr("app.main.get_customer", lambda customer_id: alex.model_copy(deep=True))

    response = client.delete("/me/goals/not_a_real_goal")

    assert response.status_code == 404
    assert response.json()["detail"] == "Goal not found"


def test_update_spending_categories_updates_expenses_and_savings(
    monkeypatch,
    alex,
) -> None:
    monkeypatch.setattr("app.main.get_customer", lambda customer_id: alex.model_copy(deep=True))
    monkeypatch.setattr(
        "app.main.save_customer_profile",
        lambda profile, email=None: profile,
    )

    response = client.put(
        "/me/spending-categories",
        json={
            "categories": {
                "Housing": 1900,
                "Groceries": 600,
                "Dining": 250,
                "Transport": 300,
                "Subscriptions": 80,
                "Other": 400,
            }
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["spendingCategories"]["Housing"] == 1900
    expected_expenses = 1900 + 600 + 250 + 300 + 80 + 400
    assert body["monthlyExpenses"] == expected_expenses
    assert body["monthlySavings"] == alex.monthlyIncome - expected_expenses
    assert any("Housing is your largest" in insight for insight in body["insights"])


def test_update_spending_categories_rejects_negative_amount(monkeypatch, alex) -> None:
    monkeypatch.setattr("app.main.get_customer", lambda customer_id: alex.model_copy(deep=True))

    response = client.put(
        "/me/spending-categories",
        json={"categories": {"Housing": -1}},
    )

    assert response.status_code == 422


def test_manage_agent_returns_reviewable_goal_proposal() -> None:
    response = client.post(
        "/agent/manage",
        json={
            "message": "Create a car goal for $12,000 with $400 monthly",
            "history": [],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["operations"][0]["operation"] == "create"
    assert body["proposalToken"]
    assert body["preview"][0]["label"].startswith("Add goal:")
    assert "nothing has been saved" in body["message"]


def test_confirmed_agent_proposal_updates_profile_and_recalculates_savings(
    monkeypatch,
    alex,
) -> None:
    monkeypatch.setattr("app.main.get_customer", lambda customer_id: alex.model_copy(deep=True))
    monkeypatch.setattr(
        "app.main.save_customer_profile",
        lambda profile, email=None: profile,
    )

    token = create_proposal_token(
        alex,
        [SetProfileOperation(
            operation="set",
            resource="profile",
            field="monthlyIncome",
            value=6000,
        )],
    )
    response = client.post(
        "/agent/proposals/apply",
        json={"proposalToken": token},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["monthlyIncome"] == 6000
    assert body["monthlyExpenses"] == alex.monthlyExpenses
    assert body["monthlySavings"] == 6000 - alex.monthlyExpenses
    assert body["insights"][-1] == (
        "You are saving approximately 36% of monthly income."
    )
    assert len(body["goals"]) == len(alex.goals)


def test_confirmed_agent_proposal_persists_in_mock_mode(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("FUTURE_YOU_MOCK_STATE_DIR", str(tmp_path))
    proposal = client.post(
        "/agent/manage",
        json={
            "message": "Create a bicycle goal for $2,000 with $100 monthly",
            "history": [],
        },
    )
    assert proposal.status_code == 200

    response = client.post(
        "/agent/proposals/apply",
        json={"proposalToken": proposal.json()["proposalToken"]},
    )

    assert response.status_code == 200
    assert any(goal["name"] == "Bicycle" for goal in response.json()["goals"])
    saved_profile = (tmp_path / "alex.json").read_text(encoding="utf-8")
    assert '"name": "Bicycle"' in saved_profile


def test_apply_endpoint_rejects_client_supplied_operations(monkeypatch, alex) -> None:
    monkeypatch.setattr("app.main.get_customer", lambda customer_id: alex.model_copy(deep=True))

    response = client.post(
        "/agent/proposals/apply",
        json={
            "operations": [
                {
                    "operation": "set",
                    "resource": "profile",
                    "field": "monthlyExpenses",
                    "value": 99999,
                }
            ]
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "proposalToken"]


def test_apply_endpoint_rejects_tampered_proposal_token(monkeypatch, alex) -> None:
    monkeypatch.setattr("app.main.get_customer", lambda customer_id: alex.model_copy(deep=True))
    token = create_proposal_token(
        alex,
        [SetProfileOperation(
            operation="set",
            resource="profile",
            field="monthlyIncome",
            value=6000,
        )],
    )

    response = client.post(
        "/agent/proposals/apply",
        json={"proposalToken": f"{token[:-1]}x"},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Invalid proposal token"


def test_apply_endpoint_rejects_stale_profile_preview(monkeypatch, alex) -> None:
    token = create_proposal_token(
        alex,
        [SetProfileOperation(
            operation="set",
            resource="profile",
            field="monthlyIncome",
            value=6000,
        )],
    )
    changed = alex.model_copy(update={"currentBalance": alex.currentBalance + 1})
    monkeypatch.setattr("app.main.get_customer", lambda customer_id: changed)

    response = client.post(
        "/agent/proposals/apply",
        json={"proposalToken": token},
    )

    assert response.status_code == 409
    assert "profile changed" in response.json()["detail"]


def test_simulate_endpoint_returns_all_goal_impacts() -> None:
    response = client.post(
        "/simulate",
        json={
            "customerId": "alex",
            "question": "What happens if I buy a $2,000 laptop?",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["result"]["after"]["balance"] == 6000
    assert body["result"]["riskLevel"] == "Medium"
    assert len(body["result"]["goalImpacts"]) == 3
    assert "$8,000.00 to $6,000.00" in body["explanation"]
    assert "timeline is unchanged" in body["explanation"]


def test_afford_question_with_explicit_amount_is_supported() -> None:
    response = client.post(
        "/simulate",
        json={
            "customerId": "alex",
            "question": "Can I afford a $3,000 trip to Japan next year?",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["scenario"]["scenarioType"] == "one_off_purchase"
    assert body["scenario"]["amount"] == 3000
    assert body["scenario"]["horizonMonths"] == 12
    assert body["scenario"]["goalId"] == "japan_holiday"
    goals = {goal["goalId"]: goal for goal in body["result"]["goalImpacts"]}
    assert goals["house_deposit"]["monthsAfter"] == 18
    assert goals["japan_holiday"]["monthsBefore"] == 6
    assert goals["japan_holiday"]["monthsAfter"] == 6
    assert body["result"]["atEventBefore"]["balance"] == 12500
    assert body["result"]["after"]["balance"] == 12500
    assert body["result"]["fundedFromGoal"] == 3000
    assert body["result"]["riskLevel"] == "Low"
    assert "month 12" in body["explanation"]


def test_extra_savings_can_target_named_goal_through_api() -> None:
    response = client.post(
        "/simulate",
        json={
            "customerId": "alex",
            "question": "What if I save an extra $50 per week for my emergency fund?",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["scenario"]["goalId"] == "emergency_fund"
    goals = {goal["goalId"]: goal for goal in body["result"]["goalImpacts"]}
    assert goals["house_deposit"]["monthsAfter"] == 18
    assert goals["emergency_fund"]["monthsAfter"] == 3


def test_zero_amount_returns_coach_guidance() -> None:
    response = client.post(
        "/simulate",
        json={"customerId": "alex", "question": "What if I buy a $0 laptop?"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["explanation"]
    assert body["result"] is None


def test_stock_question_returns_coach_guidance() -> None:
    response = client.post(
        "/simulate",
        json={
            "customerId": "alex",
            "question": "I want to buy stocks, do you have any recommendations?",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["result"] is None
    assert "stock" in body["explanation"].lower() or "invest" in body["explanation"].lower()


def test_bank_account_question_returns_coach_guidance() -> None:
    response = client.post(
        "/simulate",
        json={
            "customerId": "alex",
            "question": "I want to open a bank account, how do I do that?",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["result"] is None
    assert "account" in body["explanation"].lower()


def test_laptop_without_price_uses_estimated_amount() -> None:
    response = client.post(
        "/simulate",
        json={
            "customerId": "alex",
            "question": "What happens if I buy a laptop?",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["scenario"]["amount"] == 2000
    assert body["result"]["after"]["balance"] == 6000


@pytest.mark.parametrize(
    ("question", "cash_flow", "house_months", "risk"),
    [
        ("What if my rent increases by $100 per week?", 916.67, 26, "High"),
        ("What if I save an extra $50 per week?", 1566.67, 18, "Low"),
    ],
)
def test_simulate_endpoint_core_recurring_scenarios(
    question: str,
    cash_flow: float,
    house_months: int,
    risk: str,
) -> None:
    response = client.post(
        "/simulate",
        json={"customerId": "alex", "question": question},
    )

    assert response.status_code == 200
    result = response.json()["result"]
    house = next(
        goal for goal in result["goalImpacts"] if goal["goalId"] == "house_deposit"
    )
    assert result["after"]["monthlyCashFlow"] == cash_flow
    assert house["monthsAfter"] == house_months
    assert result["riskLevel"] == risk
