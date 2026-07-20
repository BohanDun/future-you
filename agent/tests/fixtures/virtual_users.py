"""Synthetic customer profiles for agent tests — not used in production demo data."""

from app.models.customer import CustomerProfile, FinancialGoal


def build_sam() -> CustomerProfile:
    """Tight budget: small savings buffer, purchases hit goals harder."""
    return CustomerProfile(
        customerId="sam",
        name="Sam",
        currentBalance=900,
        monthlyIncome=2800,
        monthlyExpenses=2650,
        monthlySavings=150,
        goals=[
            FinancialGoal(
                goalId="emergency_fund",
                name="Emergency Fund",
                target=2000,
                current=400,
                monthlyContribution=100,
            ),
            FinancialGoal(
                goalId="house_deposit",
                name="House Deposit",
                target=15000,
                current=1200,
                monthlyContribution=50,
            ),
        ],
        spending={
            "dining": {"May": 180, "June": 210},
        },
        spendingCategories={"housing": 1400, "dining": 210, "transport": 140},
        insights=["Your dining spending increased by approximately 17% from May to June."],
    )


def build_jordan() -> CustomerProfile:
    """Balanced profile: similar stress to Alex but different numbers."""
    return CustomerProfile(
        customerId="jordan",
        name="Jordan",
        currentBalance=6500,
        monthlyIncome=5200,
        monthlyExpenses=4100,
        monthlySavings=1100,
        goals=[
            FinancialGoal(
                goalId="house_deposit",
                name="House Deposit",
                target=25000,
                current=6500,
                monthlyContribution=600,
            ),
            FinancialGoal(
                goalId="japan_holiday",
                name="Japan Holiday",
                target=4000,
                current=1500,
                monthlyContribution=250,
            ),
            FinancialGoal(
                goalId="emergency_fund",
                name="Emergency Fund",
                target=6000,
                current=3000,
                monthlyContribution=250,
            ),
        ],
        spending={
            "dining": {"May": 320, "June": 380},
        },
        spendingCategories={"housing": 1900, "dining": 380, "groceries": 320},
        insights=["Your dining spending increased by approximately 19% from May to June."],
    )


def build_riley() -> CustomerProfile:
    """Comfortable saver: large buffer, lower risk on moderate purchases."""
    return CustomerProfile(
        customerId="riley",
        name="Riley",
        currentBalance=22000,
        monthlyIncome=7200,
        monthlyExpenses=4200,
        monthlySavings=3000,
        goals=[
            FinancialGoal(
                goalId="house_deposit",
                name="House Deposit",
                target=40000,
                current=18000,
                monthlyContribution=1500,
            ),
            FinancialGoal(
                goalId="emergency_fund",
                name="Emergency Fund",
                target=10000,
                current=8000,
                monthlyContribution=500,
            ),
        ],
        spending={
            "dining": {"May": 400, "June": 420},
        },
        spendingCategories={"housing": 2200, "dining": 420, "transport": 300},
        insights=["Your dining spending increased by approximately 5% from May to June."],
    )


VIRTUAL_USERS: dict[str, CustomerProfile] = {
    "sam": build_sam(),
    "jordan": build_jordan(),
    "riley": build_riley(),
}
