# Future You — Frontend (Person 1)

React + TypeScript + Vite + Material UI + Recharts implementation of the
Future You dashboard, AI chat, and before/after simulator, per the project
spec (sections 6.1 and 6.2).

## Run it

```bash
npm install
npm run dev
```

Opens at http://localhost:5173. No backend required — it runs entirely on
mock data out of the box.

## Structure

```
src/
  data/mockCustomer.ts       Demo profile "Alex" — matches spec section 9
  lib/
    financialTools.ts        TS port of spec section 8 (cash flow, goal
                              completion, purchase, recurring expense,
                              extra savings, risk rules)
    scenarioParser.ts        Lightweight stand-in for Bedrock's NLU step
    api.ts                   *** The one file Person 3 needs to edit ***
    format.ts                Currency/months formatting helpers
  theme/theme.ts              MUI theme — palette, type scale, tokens
  components/
    Layout/Header.tsx
    Dashboard/                Balance/income/expense/savings cards,
                               goal progress cards, spending chart
    Chat/                     Chat interface, suggested questions,
                               agent + simulator orchestration
    Simulation/                Before/after comparison, risk badge,
                               "Horizon" signature visual
  App.tsx
  main.tsx
```

## Connecting the real backend

Everything the frontend needs from the backend goes through
`src/lib/api.ts`:

- `askFutureYou(question)` → `POST {VITE_API_URL}/ask` with `{ question }`,
  expects `{ explanation, simulation }` back (see `SimulationResult` type
  in `financialTools.ts` for the exact shape the UI renders).
- `fetchCustomerProfile()` → `GET {VITE_API_URL}/customer`, expects a
  `CustomerProfile` (see `data/mockCustomer.ts`).

Copy `.env.example` to `.env.local` and set `VITE_API_URL` once API Gateway
is live — the mock fallback in `api.ts` switches off automatically. No
other file needs to change.

## Design notes

Palette and type system are in `src/theme/theme.ts`. The signature visual
is the "Horizon" (`components/Simulation/Horizon.tsx`) — the arc between
Now and Future You, colored by risk level, used on every simulation
result.

## Deploying

`npm run build` outputs to `dist/`, ready for AWS Amplify hosting per the
spec's tech stack (section 5).
