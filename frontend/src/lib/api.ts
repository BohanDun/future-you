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
  calculateAffordability as calculateAffordabilityLocally,
  calculateGoalAllocation as calculateGoalAllocationLocally,
  calculateStressTest as calculateStressTestLocally,
  runSimulation,
  toBackendGoalId,
  type AffordabilitySummary,
  type GoalAllocationResult,
  type ParsedScenario,
  type RiskLevel,
  type SimulationResult,
  type StressTestResult,
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
  spendingCategories?: Record<string, number>;
  insights?: string[];
}

interface BackendScenario {
  scenarioType: 'one_off_purchase' | 'recurring_expense' | 'extra_savings' | 'unknown';
  amount: number | null;
  frequency: string | null;
  description: string | null;
  goalId?: string | null;
}

interface BackendResponse {
  success: boolean;
  customer: BackendCustomer;
  scenario: BackendScenario;
  result: {
    before: { balance: number; monthlyCashFlow: number; goalMonths: number | null };
    after: { balance: number; monthlyCashFlow: number; goalMonths: number | null };
    riskLevel: string;
    beforeRiskLevel?: string;
    riskReasons?: string[];
    goalImpacts?: Array<{
      goalId: string;
      goalName: string;
      monthsBefore: number | null;
      monthsAfter: number | null;
      monthlyContributionBefore: number;
      monthlyContributionAfter: number;
    }>;
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
    spendingCategories: customer.spendingCategories
      ? Object.entries(customer.spendingCategories).map(([category, amount]) => ({
          category: category[0].toUpperCase() + category.slice(1),
          amount,
        }))
      : mockCustomer.spendingCategories,
    insights: customer.insights ?? mockCustomer.insights,
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
    goalId: response.scenario.goalId ?? undefined,
  };
  const goalImpacts = response.result.goalImpacts?.map((goal) => ({
    goalId: goal.goalId,
    goalName: goal.goalName,
    monthsBefore: goal.monthsBefore ?? Infinity,
    monthsAfter: goal.monthsAfter ?? Infinity,
  }));

  return {
    balanceBefore: response.result.before.balance,
    balanceAfter: response.result.after.balance,
    monthlySavingsBefore: response.result.before.monthlyCashFlow,
    monthlySavingsAfter: response.result.after.monthlyCashFlow,
    goals: goalImpacts ?? (primaryGoal
      ? [{
          goalId: primaryGoal.goalId,
          goalName: primaryGoal.name,
          monthsBefore: beforeMonths,
          monthsAfter: afterMonths,
        }]
      : []),
    riskBefore: (response.result.beforeRiskLevel ?? 'Low') as RiskLevel,
    riskAfter: response.result.riskLevel as RiskLevel,
    riskReasons: response.result.riskReasons ?? [],
    recommendation: response.result.recommendation?.description ?? '',
    scenario,
  };
}

function explainLocally(result: SimulationResult): string {
  const {
    scenario,
    balanceAfter,
    monthlySavingsBefore,
    monthlySavingsAfter,
    goals,
    riskAfter,
  } = result;
  const goalIdMap: Record<string, string> = {
    house_deposit: 'house',
    japan_holiday: 'japan',
    emergency_fund: 'emergency',
  };
  const requestedGoalId = scenario.goalId
    ? (goalIdMap[scenario.goalId] ?? scenario.goalId)
    : undefined;
  const primaryGoal =
    goals.find((goal) => requestedGoalId && goal.goalId === requestedGoalId)
    ?? goals.find((goal) => goal.monthsBefore !== goal.monthsAfter)
    ?? goals[0];
  if (!primaryGoal) {
    return `The simulation is complete. ${result.recommendation}`.trim();
  }

  const delay = primaryGoal.monthsAfter === Infinity
    ? Infinity
    : primaryGoal.monthsAfter - primaryGoal.monthsBefore;

  let scenarioImpact: string;
  if (scenario.scenarioType === 'extra_savings') {
    scenarioImpact = `Saving an extra $${scenario.amount.toLocaleString()} per week toward your ${primaryGoal.goalName} goal strengthens that plan.`;
  } else if (scenario.scenarioType === 'recurring_expense') {
    scenarioImpact = `This changes your monthly cash flow from $${monthlySavingsBefore.toLocaleString()} to $${monthlySavingsAfter.toLocaleString()}.`;
  } else {
    scenarioImpact = balanceAfter >= 0
      ? `You can cover this without your balance going negative.`
      : `This would take your balance negative — worth holding off or trimming elsewhere first.`;
  }

  const goalImpact = delay === Infinity
    ? ` Your ${primaryGoal.goalName} goal can no longer progress under this scenario.`
    : delay > 0
      ? ` It may delay your ${primaryGoal.goalName} goal by approximately ${delay} month${delay === 1 ? '' : 's'}.`
      : delay < 0
        ? ` It brings your ${primaryGoal.goalName} goal forward by about ${Math.abs(delay)} month${Math.abs(delay) === 1 ? '' : 's'}.`
        : ` It doesn't shift your ${primaryGoal.goalName} timeline.`;

  const riskNote = riskAfter === 'High' ? ' This pushes your risk level up — worth a closer look.' : '';

  return `${scenarioImpact}${goalImpact}${riskNote} ${result.recommendation}`.trim();
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

export async function fetchAffordability(
  profile: CustomerProfile,
  goalId: string,
): Promise<AffordabilitySummary> {
  if (API_URL) {
    const backendGoalId = toBackendGoalId(goalId);
    const res = await fetch(
      apiUrl(`/customer/${CUSTOMER_ID}/affordability?goalId=${encodeURIComponent(backendGoalId)}`),
    );
    if (!res.ok) throw new Error(`Future You API error: ${res.status}`);
    return (await res.json()) as AffordabilitySummary;
  }
  return calculateAffordabilityLocally(profile, goalId);
}

export async function runFinancialStressTest(
  profile: CustomerProfile,
  incomeLossMonths: number,
  unexpectedExpense: number,
): Promise<StressTestResult> {
  if (API_URL) {
    const res = await fetch(apiUrl('/stress-test'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        customerId: CUSTOMER_ID,
        incomeLossMonths,
        unexpectedExpense,
      }),
    });
    if (!res.ok) throw new Error(`Future You API error: ${res.status}`);
    const response = await res.json() as StressTestResult & {
      goalImpacts: Array<StressTestResult['goalImpacts'][number] & {
        monthsBefore: number | null;
        monthsAfter: number | null;
      }>;
    };
    return {
      ...response,
      riskLevel: response.riskLevel as RiskLevel,
      goalImpacts: response.goalImpacts.map((goal) => ({
        ...goal,
        monthsBefore: goal.monthsBefore ?? Infinity,
        monthsAfter: goal.monthsAfter ?? Infinity,
      })),
    };
  }
  return calculateStressTestLocally(profile, incomeLossMonths, unexpectedExpense);
}

export async function optimizeGoalPlan(
  profile: CustomerProfile,
  priorityGoalId: string,
  targetMonths: number,
): Promise<GoalAllocationResult> {
  if (API_URL) {
    const res = await fetch(apiUrl('/optimize-goals'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        customerId: CUSTOMER_ID,
        priorityGoalId: toBackendGoalId(priorityGoalId),
        targetMonths,
      }),
    });
    if (!res.ok) throw new Error(`Future You API error: ${res.status}`);
    const response = await res.json() as GoalAllocationResult & {
      allocations: Array<GoalAllocationResult['allocations'][number] & {
        monthsBefore: number | null;
        monthsAfter: number | null;
      }>;
    };
    return {
      ...response,
      allocations: response.allocations.map((allocation) => ({
        ...allocation,
        monthsBefore: allocation.monthsBefore ?? Infinity,
        monthsAfter: allocation.monthsAfter ?? Infinity,
      })),
    };
  }
  return calculateGoalAllocationLocally(profile, priorityGoalId, targetMonths);
}
