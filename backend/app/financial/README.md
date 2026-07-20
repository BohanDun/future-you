# Person 2 financial engine

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

Recurring expenses reduce monthly cash flow. Goal contributions are scaled proportionally so the sum remains within the new savings capacity.

Extra savings are added to the named goal contribution. If the question does not name a goal, the house deposit is used as the prototype default. Extra savings do not create income, so income-minus-expenses cash flow remains unchanged.

A one-time purchase affects a goal named in the question, such as Japan Holiday. If no goal is named, it is assumed to come from the house-deposit pool. Other goals remain unchanged.

All money is calculated with Python `Decimal` and rounded to cents with `ROUND_HALF_UP` before entering the API models.

## Decision planning

- Safe-to-Spend uses a cent-accurate binary search over the deterministic risk
  engine to find the maximum Low and Medium risk purchase for a selected goal.
- Stress Test models up to 12 months of income loss plus an optional emergency
  expense, then reports balance, emergency runway, risk reasons and goal delays.
- Goal Optimizer reallocates the existing monthly savings budget. It never
  increases total contributions above income minus expenses, and reports when
  a requested deadline is mathematically infeasible.

## Risk rules

| Level | Deterministic conditions |
| --- | --- |
| High | Negative balance or cash flow; less than one month of expenses available; a goal cannot progress; or a goal delay of 6+ months |
| Medium | Less than two months of expenses available; cash flow falls by at least 50%; or a goal delay of 2–5 months |
| Low | None of the high or medium conditions apply |

## Money Health score

The explainable Money Health score uses three capped components. The result is
deterministic and does not depend on an AI-generated rating.

| Component | Maximum | Full-score benchmark |
| --- | ---: | --- |
| Savings rate | 40 | Save at least 20% of monthly income |
| Cash reserve | 35 | Hold at least three months of expenses |
| Goal progress | 25 | Average progress across active goals |

Alex scores 77/100 (Strong): 40 points for savings rate, 24.24 points for cash
reserve coverage, and 12.5 points for goal progress.

## Verified demo outcomes

| Scenario | Result | Goal impact | Risk |
| --- | --- | --- | --- |
| Buy a $2,000 laptop | Balance $8,000 → $6,000 | House deposit 18 → 20 months | Medium |
| Rent increases $100/week | Cash flow $1,350 → $916.67/month | House deposit 18 → 26 months | High |
| Save an extra $50/week | House contribution $700 → $916.67/month | House deposit 18 → 14 months | Low |
| Save an extra $50/week for emergency fund | Emergency contribution $350 → $566.67/month | Emergency fund 5 → 3 months | Low |
| Spend $3,000 on a Japan trip | Balance $8,000 → $5,000 | Japan holiday 6 → 10 months | Medium |

## Verification

From `backend/` on Windows:

```powershell
..\.venv\Scripts\python.exe -m ruff check .
..\.venv\Scripts\python.exe -m pytest
```
