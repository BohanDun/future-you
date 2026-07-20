// ---------------------------------------------------------------------------
// API layer — this is the ONE file Person 3 needs to touch to connect the
// real backend (API Gateway → Lambda → DynamoDB/Bedrock).
//
// If VITE_API_URL is set (see .env.example), askFutureYou() calls the real
// endpoint. Otherwise it falls back to a local mock pipeline (parser +
// financial tools) so the rest of the team can build and demo the UI before
// the backend is live.
// ---------------------------------------------------------------------------

import { mockCustomer, type CustomerProfile } from '../data/mockCustomer';
import { parseQuestion } from './scenarioParser';
import {
  runSimulation,
  type ParsedScenario,
  type RiskLevel,
  type SimulationResult,
} from './financialTools';

export interface AskFutureYouResponse {
  explanation: string;
  simulation: SimulationResult;
}

const API_URL = import.meta.env.VITE_API_URL as string | undefined;
const CUSTOMER_ID = 'alex';

interface BackendGoal {
  goalId: string;
  name: string;
  target: number;
  current: number;
  monthlyContribution: number;
}

interface BackendCustomer {
  customerId: string;
  name: string;
  currentBalance: number;
  monthlyIncome: number;
  monthlyExpenses: number;
  monthlySavings: number;
  goals: BackendGoal[];
  spending: Record<string, Record<string, number>>;
}

interface BackendScenario {
  scenarioType: 'one_off_purchase' | 'recurring_expense' | 'extra_savings' | 'unknown';
  amount: number | null;
  frequency: string | null;
  description: string | null;
}

interface BackendResponse {
  success: boolean;
  customer: BackendCustomer;
  scenario: BackendScenario;
  result: {
    before: { balance: number; monthlyCashFlow: number; goalMonths: number | null };
    after: { balance: number; monthlyCashFlow: number; goalMonths: number | null };
    riskLevel: string;
    recommendation: { description: string; weeklyAmount: number | null } | null;
  };
  explanation: string | null;
}

function apiUrl(path: string): string {
  return `${API_URL?.replace(/\/$/, '')}${path}`;
}

function toCustomerProfile(customer: BackendCustomer): CustomerProfile {
  const dining = customer.spending.dining ?? {};
  return {
    name: customer.name,
    balance: customer.currentBalance,
    monthlyIncome: customer.monthlyIncome,
    monthlyExpenses: customer.monthlyExpenses,
    monthlySavings: customer.monthlySavings,
    goals: customer.goals.map((goal) => ({
      id: goal.goalId,
      name: goal.name,
      target: goal.target,
      current: goal.current,
      monthlyContribution: goal.monthlyContribution,
    })),
    diningSpend: Object.entries(dining).map(([month, amount]) => ({
      month: month.slice(0, 3),
      amount,
    })),
    spendingCategories: mockCustomer.spendingCategories,
  };
}

function toSimulationResult(response: BackendResponse): SimulationResult {
  const beforeMonths = response.result.before.goalMonths ?? Infinity;
  const afterMonths = response.result.after.goalMonths ?? Infinity;
  const primaryGoal = response.customer.goals.find((goal) => goal.goalId === 'house_deposit');
  const scenario: ParsedScenario = {
    scenarioType: response.scenario.scenarioType as ParsedScenario['scenarioType'],
    amount: response.scenario.amount ?? 0,
    description: response.scenario.description ?? 'Financial scenario',
  };

  return {
    balanceBefore: response.result.before.balance,
    balanceAfter: response.result.after.balance,
    monthlySavingsBefore: response.result.before.monthlyCashFlow,
    monthlySavingsAfter: response.result.after.monthlyCashFlow,
    goals: primaryGoal
      ? [{
          goalId: primaryGoal.goalId,
          goalName: primaryGoal.name,
          monthsBefore: beforeMonths,
          monthsAfter: afterMonths,
        }]
      : [],
    riskBefore: 'Low',
    riskAfter: response.result.riskLevel as RiskLevel,
    recommendation: response.result.recommendation?.description ?? '',
    scenario,
  };
}

function explainLocally(result: SimulationResult): string {
  const { scenario, balanceAfter, goals, riskAfter } = result;
  const primaryGoal = goals[0];
  const delay = primaryGoal.monthsAfter === Infinity ? 0 : primaryGoal.monthsAfter - primaryGoal.monthsBefore;

  const affordability =
    balanceAfter >= 0
      ? `You can cover this without your balance going negative.`
      : `This would take your balance negative — worth holding off or trimming elsewhere first.`;

  const goalImpact =
    delay > 0
      ? ` It may delay your ${primaryGoal.goalName.toLowerCase()} goal by approximately ${delay} month${delay === 1 ? '' : 's'}.`
      : delay < 0
      ? ` It actually brings your ${primaryGoal.goalName.toLowerCase()} goal forward by about ${Math.abs(delay)} month${Math.abs(delay) === 1 ? '' : 's'}.`
      : ` It doesn't shift your ${primaryGoal.goalName.toLowerCase()} timeline.`;

  const riskNote = riskAfter === 'High' ? ' This pushes your risk level up — worth a closer look.' : '';

  return `${affordability}${goalImpact}${riskNote} ${result.recommendation}`.trim();
}

export async function askFutureYou(question: string): Promise<AskFutureYouResponse> {
  if (API_URL) {
    const res = await fetch(apiUrl('/simulate'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ customerId: CUSTOMER_ID, question }),
    });
    if (!res.ok) {
      throw new Error(`Future You API error: ${res.status}`);
    }
    const response = (await res.json()) as BackendResponse;
    return {
      explanation: response.explanation ?? 'Simulation complete.',
      simulation: toSimulationResult(response),
    };
  }

  // --- local fallback (no backend yet) ---
  await new Promise((r) => setTimeout(r, 550)); // small delay so the UI's loading state is visible
  const scenario = parseQuestion(question);
  const simulation = runSimulation(mockCustomer, scenario);
  return { explanation: explainLocally(simulation), simulation };
}

export async function fetchCustomerProfile(): Promise<CustomerProfile> {
  if (API_URL) {
    const res = await fetch(apiUrl(`/customer/${CUSTOMER_ID}`));
    if (!res.ok) throw new Error(`Future You API error: ${res.status}`);
    return toCustomerProfile((await res.json()) as BackendCustomer);
  }
  await new Promise((r) => setTimeout(r, 200));
  return mockCustomer;
}
