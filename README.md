# Future You

Future You is a financial what-if simulator with a React frontend and a
FastAPI backend. It can run locally with mock customer and AI data, or use
AWS DynamoDB and Amazon Bedrock through environment configuration.

## Project structure

```text
future-you/
|-- frontend/                 React, TypeScript and Vite application
|   |-- src/
|   |   |-- components/       Dashboard, chat, planning and simulation UI
|   |   |-- data/             Local mock customer data
|   |   |-- lib/              API client and deterministic local fallback
|   |   `-- theme/            Material UI theme
|   |-- .env.example
|   |-- package.json
|   `-- vite.config.ts
|-- backend/                  FastAPI application and Lambda entry point
|   |-- app/
|   |   |-- agent/            Financial question parsing
|   |   |-- financial/        Auditable financial calculation engine
|   |   |-- models/           Pydantic request and response models
|   |   |-- services/         Customer, planning and Bedrock services
|   |   |-- lambda_handler.py
|   |   `-- main.py
|   |-- tests/
|   |-- .env.example
|   `-- requirements.txt
`-- README.md
```

## Run locally

### Backend

```bash
cd backend
python -m venv .venv
# Windows PowerShell: .\.venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
# Windows PowerShell: Copy-Item .env.example .env
# macOS/Linux: cp .env.example .env
uvicorn app.main:app --reload
```

The API runs at <http://127.0.0.1:8000>. Interactive documentation is at
<http://127.0.0.1:8000/docs>.

The default settings use mock data and do not invoke Bedrock:

```env
DATA_SOURCE=mock
AI_MODE=mock
```

### Frontend

In a second terminal:

```bash
cd frontend
npm install
# Windows PowerShell: Copy-Item .env.example .env.local
# macOS/Linux: cp .env.example .env.local
npm run dev
```

The frontend runs at <http://localhost:5173>. Set `VITE_API_URL` in
`frontend/.env.local` to the local backend or the deployed API Gateway base
URL. Leave it empty to use the frontend's local mock pipeline.

## API

- `GET /` describes the service and its available routes.
- `GET /health` checks backend availability.
- `GET /customer/{customer_id}` returns a customer profile.
- `GET /customer/{customer_id}/health-score` returns an explainable 0-100
  score for savings rate, reserve coverage and goal progress.
- `GET /customer/{customer_id}/affordability` returns Low, Medium and High
  purchase boundaries for a selected financial goal.
- `POST /simulate` parses a financial question and returns the simulation.
- `POST /stress-test` models income-loss and emergency-expense shocks.
- `POST /optimize-goals` reallocates the existing monthly savings budget to
  meet a selected goal deadline without creating new money.

Example request:

```json
{
  "customerId": "alex",
  "question": "Can I buy a laptop for $2000?"
}
```

## Verification

```bash
cd frontend
npm run lint
npm run build

cd ../backend
python -m ruff check .
python -m pytest
```

Frontend production files are generated in `frontend/dist/`. Backend Lambda
artifacts under `backend/build/` and `backend/future-you-backend.zip` are not
committed.

## Person 2 financial engine

The deterministic financial engine is in `backend/app/financial/`. Synthetic
customer and transaction data live in `backend/data/`. The engine calculates
all money and goal outcomes before Bedrock receives the result, so the AI does
not invent financial figures.

See `backend/app/financial/README.md` for formulas, risk thresholds, allocation
assumptions, and the verified demo outcomes.

The frontend adds an explainable Money Health score and a Decision Lab with an
interactive Safe-to-Spend slider, saved scenario comparison, configurable
stress testing, a 12-month cash recovery forecast, goal allocation planning,
future timeline visualization, and deterministic recovery options.
