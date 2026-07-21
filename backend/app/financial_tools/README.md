# Person 2 financial tools

This package is the deterministic source of truth for Future You calculations. It has no AWS, HTTP, or generative-AI dependency.

## Data

- `backend/data/customers/alex.json` contains the fictional customer and goals.
- `backend/data/transactions/alex.csv` contains 19 synthetic transactions.
- The latest transaction month is aggregated into income, expenses, savings, and spending categories.
- Dashboard insights are generated from transaction history rather than stored as fixed strings.

## Formulas

```text
Monthly cash flow = monthly income - monthly expenses
Months to goal = ceil((target - current savings) / monthly contribution)
New balance = current balance - one-time purchase
Weekly amount per month = weekly amount * 52 / 12
```

Recurring expenses reduce monthly cash flow. Unallocated monthly cash absorbs the increase
first. Only when the remaining cash flow is below the contributions of unfinished goals are
those active contributions scaled proportionally. Goals already completed by a future event
do not consume contribution capacity.

Extra savings increase monthly saving capacity by the frequency-adjusted amount. When the
customer names a goal, the same amount is also allocated to that goal's contribution. When no
goal is named, goal timelines remain unchanged rather than silently selecting the first goal.

A one-time purchase uses a named goal only when the customer clearly identifies it. Otherwise
it comes from projected liquid cash and does not silently consume an unrelated goal. For a
future purchase, cash flow and capped goal contributions are projected month by month before
the event.

All money is calculated with Python `Decimal` and rounded to cents with `ROUND_HALF_UP` before entering the API models.

## Risk rules

| Level | Deterministic conditions |
| --- | --- |
| High | Negative balance or cash flow; less than one month of expenses available; a goal cannot progress; or a goal delay of 6+ months |
| Medium | Less than two months of expenses available; cash flow falls by at least 50%; or a goal delay of 2–5 months |
| Low | None of the high or medium conditions apply |

## Verified demo outcomes

| Scenario | Result | Goal impact | Risk |
| --- | --- | --- | --- |
| Buy a $2,000 laptop | Balance $8,000 → $6,000 | Existing goal timelines unchanged | Medium |
| Rent increases $100/week | Cash flow $1,350 → $916.67/month | House deposit 18 → 26 months | High |
| Save an extra $50/week without naming a goal | Monthly saving capacity $1,350 → $1,566.67 | Existing goal timelines unchanged | Low |
| Save an extra $50/week for emergency fund | Emergency contribution $350 → $566.67/month | Emergency fund 5 → 3 months | Low |
| Spend $3,000 on a Japan trip next year | Projected liquid balance remains $12,500 because the named goal funds it | Japan holiday reaches its target before the event | Low |

## Verification

From `backend/` on Windows:

```powershell
..\.venv\Scripts\python.exe -m ruff check .
..\.venv\Scripts\python.exe -m pytest
```
