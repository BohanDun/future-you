# Future You

Future You is a financial what-if simulator with a React frontend, a FastAPI
backend, and a standalone AI agent module. It can run locally with mock
customer data, or use AWS DynamoDB and Amazon Bedrock through environment
configuration.

**Core principle:** the AI agent understands and explains. The financial tools
calculate. Bedrock never invents money or goal outcomes.

## How to use

### Quick start (full stack)

You need **two terminals** — one for the backend, one for the frontend.

**Terminal 1 — backend + agent**

```bash
cd backend
python -m venv .venv
# Windows PowerShell: .\.venv\Scripts\Activate.ps1
# macOS/Linux:
source .venv/bin/activate
pip install -r requirements.txt

# Required so Python can import the top-level agent/ package:
export PYTHONPATH="/path/to/future-you-main/backend:/path/to/future-you-main"

# Mock mode — no API key needed (good for offline dev and tests):
export AI_MODE=mock

uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Replace `/path/to/future-you-main` with your actual repo path.

**Terminal 2 — frontend**

```bash
cd frontend
npm install
cp .env.example .env.local   # Windows: Copy-Item .env.example .env.local
npm run dev
```

Open **http://127.0.0.1:5173** in your browser.

Make sure `frontend/.env.local` points at the backend:

```env
VITE_API_URL=http://127.0.0.1:8000
```

### Using the chat

The demo customer is **Alex**. In the **Ask Future You** chat you can ask:

**What-if questions (runs a simulation + shows numbers below the chat)**

- `What happens if I buy a $2,000 laptop?`
- `What if my rent increases by $100 per week?`
- `What if I save an extra $50 per week for my emergency fund?`
- `Should I buy a laptop?` — uses a reasonable estimated price when no amount is given

**General money questions (free-form coach reply — no simulation panel)**

- `I want to buy stocks, do you have any recommendations?`
- `I want to open a bank account, how do I do that?`
- `How should I budget better?`

The agent acts as a financial wellbeing coach: warm, practical, and grounded in
Alex's profile (balance, savings, goals). For what-if questions it uses exact
numbers from the calculation engine — it does not invent figures.

### Live AI with Amazon Bedrock (optional)

To use the real Bedrock model instead of mock responses:

```bash
export PYTHONPATH="/path/to/future-you-main/backend:/path/to/future-you-main"
export AI_MODE=bedrock
export AWS_REGION_NAME=ap-southeast-2
export BEDROCK_MODEL_ID=amazon.nova-lite-v1:0

# ⚠️ Use your own Bedrock API key here — do not commit it or share it in git.
export AWS_BEARER_TOKEN_BEDROCK='paste-your-own-api-key-here'

uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

> **Important:** Replace `paste-your-own-api-key-here` with **your own** Bedrock
> API key. Never commit keys to the repo, paste them into README files, or check
> them into `.env` files that are tracked by git. Short-lived keys expire — generate
> a fresh one when needed.

Smoke-test Bedrock connectivity:

```bash
export AWS_BEARER_TOKEN_BEDROCK='paste-your-own-api-key-here'
cd backend && source .venv/bin/activate
export PYTHONPATH="../:."
python -m agent.scripts.test_bedrock
```

Default model: `amazon.nova-lite-v1:0` in `ap-southeast-2`.

## Project structure

```text
future-you/
├── agent/                    Person 4 — AI agent (Bedrock + prompts + fallback)
│   ├── service.py            Public API: parse, explain, coach routing
│   ├── coach.py              Free-form financial coaching (non-simulation)
│   ├── bedrock_client.py     Amazon Bedrock Converse client
│   ├── question_parser.py    Natural-language question → ParsedScenario
│   ├── explainer.py          Simulation result → plain-language explanation
│   ├── scenario_parser.py    Mock parser fallback
│   ├── prompts.py            System prompts for understanding and explanation
│   ├── scripts/              Bedrock connectivity smoke test
│   └── tests/                Agent unit tests + virtual user fixtures
├── frontend/                 React, TypeScript and Vite application
│   ├── src/
│   │   ├── components/       Dashboard, chat and simulation UI
│   │   ├── data/             Local mock customer data
│   │   ├── lib/              API client and local simulation fallback
│   │   └── theme/            Material UI theme
│   ├── .env.example
│   ├── package.json
│   └── vite.config.ts
├── backend/                  FastAPI application and Lambda entry point
│   ├── app/
│   │   ├── financial/        Person 2 — deterministic calculation engine
│   │   ├── models/           Pydantic request and response models
│   │   ├── services/         Customer and simulation services
│   │   ├── lambda_handler.py
│   │   └── main.py           Imports the agent via `from agent import ...`
│   ├── data/                 Synthetic customer and transaction data
│   ├── tests/
│   ├── .env.example
│   └── requirements.txt
└── README.md
```

## Run locally

See **How to use** above for the recommended step-by-step setup. Summary:

### Backend + Agent

```bash
cd backend
source .venv/bin/activate          # or create venv first — see Quick start
export PYTHONPATH="../:."
export AI_MODE=mock                # or bedrock — see below
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

The API runs at <http://127.0.0.1:8000>. Interactive documentation is at
<http://127.0.0.1:8000/docs>.

Mock mode (no Bedrock calls — good for offline development and CI):

```env
AI_MODE=mock
DATA_SOURCE=mock
```

Live Bedrock mode — **use your own API key**:

```bash
export PYTHONPATH="../:."
export AWS_BEARER_TOKEN_BEDROCK='paste-your-own-api-key-here'
export AI_MODE=bedrock
export BEDROCK_MODEL_ID=amazon.nova-lite-v1:0
export AWS_REGION_NAME=ap-southeast-2
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Do not commit API keys. See `agent/.env.example` for agent-specific variables.

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

Example `frontend/.env.local`:

```env
VITE_API_URL=http://127.0.0.1:8000
```

## API

- `GET /health` checks backend availability.
- `GET /customer/{customer_id}` returns a customer profile.
- `POST /simulate` parses a financial question and returns the simulation.

Example request:

```json
{
  "customerId": "alex",
  "question": "Can I buy a laptop for $2000?"
}
```

Example flow:

```text
Customer question
    → agent parses scenario (Bedrock or mock fallback)
    → if what-if with an amount: backend runs financial tools → agent explains numbers
    → if general money question: agent coach replies from profile (no simulation)
    → JSON response returned to frontend
```

`POST /simulate` returns `result: null` for coach-only replies; the frontend
shows the explanation in chat without the comparison panel.

## Verification

```bash
cd frontend
npm run lint
npm run build

cd ../backend
python -m ruff check . ../agent
python -m pytest
python -m pytest ../agent/tests -q
```

Frontend production files are generated in `frontend/dist/`. Backend Lambda
artifacts under `backend/build/` and `backend/future-you-backend.zip` are not
committed.

## Person 4 — AI agent

The agent lives in the top-level `agent/` folder and is imported by the backend
simulate endpoint. It has three jobs:

1. **Understand the question** — convert natural language into a structured
   `ParsedScenario` (`scenarioType`, `amount`, `frequency`, `description`,
   `goalId`).
2. **Explain the result** — turn the calculated simulation output into a short,
   supportive answer without changing any numbers.
3. **Coach freely** — answer general money questions (investing basics, bank
   accounts, budgeting) when the question is not a numeric what-if.

### Key files

| File | Purpose |
|------|---------|
| `agent/service.py` | Public entry point; routes simulation vs coach |
| `agent/coach.py` | Free-form Bedrock coaching for non-simulation questions |
| `agent/prompts.py` | Bedrock system prompts |
| `agent/bedrock_client.py` | Calls `bedrock-runtime` Converse API |
| `agent/scenario_parser.py` | Mock parser used when `AI_MODE=mock` or Bedrock fails |
| `agent/fallback.py` | Mock explanations and coach replies |

### Bedrock smoke test

Use **your own** API key:

```bash
export AWS_BEARER_TOKEN_BEDROCK='paste-your-own-api-key-here'
cd backend && source .venv/bin/activate
export PYTHONPATH="../:."
python -m agent.scripts.test_bedrock
```

Model default: `amazon.nova-lite-v1:0` in `ap-southeast-2`.

### Agent tests

Agent tests include virtual users (`Sam`, `Jordan`, `Riley`) under
`agent/tests/fixtures/virtual_users.py` for profile-specific risk and goal
behaviour checks.

```bash
cd backend && source .venv/bin/activate
python -m pytest ../agent/tests -q
```

## Person 2 — financial engine

The deterministic financial engine is in `backend/app/financial/`. Synthetic
customer and transaction data live in `backend/data/`. The engine calculates
all money and goal outcomes before Bedrock receives the result, so the AI does
not invent financial figures.

See `backend/app/financial/README.md` for formulas, risk thresholds, allocation
assumptions, and the verified demo outcomes.

## Team integration notes

| Part | Owner | Backend touchpoint |
|------|-------|-------------------|
| Frontend | Person 1 | Calls `POST /simulate` via `frontend/src/lib/api.ts` |
| Financial tools | Person 2 | `backend/app/financial/` + `backend/data/` |
| Backend / AWS | Person 3 | `backend/app/main.py`, Lambda, API Gateway |
| AI agent | Bohan Dun (Person 4) | `agent/` imported in `backend/app/main.py` |

When deploying Lambda, include both `backend/app/` and the top-level `agent/`
package in the deployment artifact, with the repo root on `PYTHONPATH`.

## Contributors

- **Bohan Dun** ([@BohanDun](https://github.com/BohanDun)) — AI agent module
  (`agent/`), Bedrock integration, coach mode, enrichment, tests, and README
  setup docs
