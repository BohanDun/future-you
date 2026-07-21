from app.financial_tools.risk import assess_financial_risk


def test_low_risk_when_buffers_remain_healthy() -> None:
    result = assess_financial_risk(
        monthly_cash_flow_before=1350,
        monthly_cash_flow_after=1350,
        available_balance_after=8000,
        monthly_expenses=3850,
        max_goal_delay_months=0,
    )
    assert result.level == "Low"


def test_medium_risk_for_short_goal_delay_and_reduced_buffer() -> None:
    result = assess_financial_risk(
        monthly_cash_flow_before=1350,
        monthly_cash_flow_after=1350,
        available_balance_after=6000,
        monthly_expenses=3850,
        max_goal_delay_months=2,
    )
    assert result.level == "Medium"
    assert len(result.reasons) == 2


def test_high_risk_for_negative_cash_flow() -> None:
    result = assess_financial_risk(
        monthly_cash_flow_before=1350,
        monthly_cash_flow_after=-10,
        available_balance_after=8000,
        monthly_expenses=3850,
    )
    assert result.level == "High"
    assert "Monthly cash flow becomes negative." in result.reasons


def test_high_risk_for_serious_goal_delay() -> None:
    result = assess_financial_risk(
        monthly_cash_flow_before=1350,
        monthly_cash_flow_after=900,
        available_balance_after=8000,
        monthly_expenses=3850,
        max_goal_delay_months=6,
    )
    assert result.level == "High"
