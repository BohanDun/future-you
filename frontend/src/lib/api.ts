// ---------------------------------------------------------------------------
// API layer — this is the ONE file Person 3 needs to touch to connect the
// real backend (API Gateway → Lambda → DynamoDB/Bedrock).
//
// If VITE_API_URL is set (see .env.example), askFutureYou() calls the real
// endpoint. Otherwise it falls back to a local mock pipeline (parser +
// financial tools) so the rest of the team can build and demo the UI before
// the backend is live.
// ---------------------------------------------------------------------------

import { mockCustomer, type CustomerProfile, type Goal } from '../data/mockCustomer';
import { authEnabled, getAccessToken } from './auth';
import {
  type ParsedScenario,
  type RiskLevel,
  type SimulationResult,
} from './financialTools';

export interface AskFutureYouResponse {
  explanation: string;
  simulation: SimulationResult | null;
}

export interface ConversationMessage {
  role: 'user' | 'assistant';
  content: string;
}

export type AgentOperation =
  | {
      operation: 'create';
      resource: 'goal';
      values: {
        name: string;
        target: number;
        current: number;
        monthlyContribution: number;
      };
    }
  | {
      operation: 'set';
      resource: 'profile';
      field: 'currentBalance' | 'monthlyIncome' | 'monthlyExpenses';
      value: number;
    }
  | {
      operation: 'set';
      resource: 'goal';
      resourceId: string;
      field: 'name' | 'target' | 'current' | 'monthlyContribution';
      value: string | number;
    };

export interface ChangePreview {
  label: string;
  before: string | null;
  after: string;
}

export interface ManageAgentResponse {
  message: string;
  operations: AgentOperation[];
  preview: ChangePreview[];
  proposalToken?: string | null;
  clarification?: {
    missingFields: string[];
    question: string;
  } | null;
}

const API_URL = import.meta.env.VITE_API_URL as string | undefined;
const CUSTOMER_ID = 'alex';

export interface UserProfileInput {
  name: string;
  currency: string;
  currentBalance: number;
  monthlyIncome: number;
  monthlyExpenses: number;
  goals: BackendGoal[];
}

export class ProfileNotFoundError extends Error {}

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

async function apiError(res: Response, fallback: string): Promise<ApiError> {
  const body = (await res.json().catch(() => null)) as { detail?: unknown } | null;
  return new ApiError(formatApiDetail(body?.detail, fallback), res.status);
}

function formatApiDetail(detail: unknown, fallback: string): string {
  if (typeof detail === 'string' && detail.trim()) return detail;
  if (Array.isArray(detail)) {
    const messages = detail.flatMap((item) => {
      if (!item || typeof item !== 'object') return [];
      const error = item as { loc?: unknown; msg?: unknown };
      if (typeof error.msg !== 'string') return [];
      const location = Array.isArray(error.loc)
        ? error.loc.filter((part) => part !== 'body').join('.')
        : '';
      return [location ? `${location}: ${error.msg}` : error.msg];
    });
    if (messages.length) return messages.join('; ');
  }
  if (detail && typeof detail === 'object') {
    const error = detail as { message?: unknown; msg?: unknown };
    if (typeof error.message === 'string') return error.message;
    if (typeof error.msg === 'string') return error.msg;
  }
  return fallback;
}

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
  currency: string;
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
  horizonMonths?: number;
  timingLabel?: string | null;
}

interface BackendResponse {
  success: boolean;
  customer: BackendCustomer;
  scenario: BackendScenario | null;
  result: {
    before: { balance: number; monthlyCashFlow: number; goalMonths: number | null };
    atEventBefore?: { balance: number; monthlyCashFlow: number; goalMonths: number | null } | null;
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
      currentAtEvent?: number | null;
      currentAfterEvent?: number | null;
    }>;
    recommendation: { description: string; weeklyAmount: number | null } | null;
    horizonMonths?: number;
    goalContributionsByEvent?: number;
    fundedFromGoal?: number;
    fundedFromBalance?: number;
    eventRiskLevel?: string | null;
  } | null;
  explanation: string | null;
}

function apiUrl(path: string): string {
  return `${API_URL?.replace(/\/$/, '')}${path}`;
}

async function authenticatedHeaders(): Promise<Record<string, string>> {
  const token = await getAccessToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

function toCustomerProfile(customer: BackendCustomer): CustomerProfile {
  const dining = customer.spending.dining ?? {};
  return {
    name: customer.name,
    currency: customer.currency,
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

function toSimulationResult(response: BackendResponse): SimulationResult | null {
  if (!response.scenario || !response.result) {
    return null;
  }
  const beforeMonths = response.result.before.goalMonths ?? Infinity;
  const afterMonths = response.result.after.goalMonths ?? Infinity;
  const primaryGoal = response.customer.goals.find((goal) => goal.goalId === 'house_deposit');
  const scenario: ParsedScenario = {
    scenarioType: response.scenario.scenarioType as ParsedScenario['scenarioType'],
    amount: response.scenario.amount ?? 0,
    description: response.scenario.description ?? 'Financial scenario',
    goalId: response.scenario.goalId ?? undefined,
    horizonMonths: response.scenario.horizonMonths ?? 0,
    timingLabel: response.scenario.timingLabel ?? undefined,
  };
  const goalImpacts = response.result.goalImpacts?.map((goal) => ({
    goalId: goal.goalId,
    goalName: goal.goalName,
    monthsBefore: goal.monthsBefore ?? Infinity,
    monthsAfter: goal.monthsAfter ?? Infinity,
    currentAtEvent: goal.currentAtEvent ?? undefined,
    currentAfterEvent: goal.currentAfterEvent ?? undefined,
  }));

  return {
    balanceBefore: response.result.before.balance,
    balanceAfter: response.result.after.balance,
    balanceAtEventBefore: response.result.atEventBefore?.balance,
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
    goalContributionsByEvent: response.result.goalContributionsByEvent,
    fundedFromGoal: response.result.fundedFromGoal,
    fundedFromBalance: response.result.fundedFromBalance,
    eventRisk: (response.result.eventRiskLevel ?? undefined) as RiskLevel | undefined,
  };
}

export async function askFutureYou(
  question: string,
  history: ConversationMessage[] = [],
): Promise<AskFutureYouResponse> {
  if (API_URL) {
    const authHeaders = await authenticatedHeaders();
    const res = await fetch(apiUrl('/simulate'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeaders },
      body: JSON.stringify(authEnabled
        ? { question, history }
        : { customerId: CUSTOMER_ID, question, history }),
    });
    if (!res.ok) {
      throw await apiError(res, `Future You API error: ${res.status}`);
    }
    const response = (await res.json()) as BackendResponse;
    return {
      explanation: response.explanation ?? 'Thanks for your question.',
      simulation: toSimulationResult(response),
    };
  }

  throw new Error(
    'VITE_API_URL is required for Advice mode so simulations use the verified backend engine.',
  );
}

export async function fetchCustomerProfile(): Promise<CustomerProfile> {
  if (API_URL) {
    const path = authEnabled ? '/me/profile' : `/customer/${CUSTOMER_ID}`;
    const res = await fetch(apiUrl(path), { headers: await authenticatedHeaders() });
    if (authEnabled && res.status === 404) throw new ProfileNotFoundError('Profile not found');
    if (!res.ok) {
      throw await apiError(res, `Future You API error: ${res.status}`);
    }
    return toCustomerProfile((await res.json()) as BackendCustomer);
  }
  await new Promise((r) => setTimeout(r, 200));
  return mockCustomer;
}

export async function saveCurrentUserProfile(
  profile: UserProfileInput,
): Promise<CustomerProfile> {
  if (!API_URL) throw new Error('VITE_API_URL is required to save a user profile.');
  const res = await fetch(apiUrl('/me/profile'), {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      ...(await authenticatedHeaders()),
    },
    body: JSON.stringify(profile),
  });
  if (!res.ok) {
    throw await apiError(res, `Future You API error: ${res.status}`);
  }
  return toCustomerProfile((await res.json()) as BackendCustomer);
}

export async function addCurrentUserGoal(goal: Goal): Promise<CustomerProfile> {
  if (!API_URL) throw new Error('VITE_API_URL is required to add a goal.');
  const res = await fetch(apiUrl('/me/goals'), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(await authenticatedHeaders()),
    },
    body: JSON.stringify({
      goalId: goal.id,
      name: goal.name,
      target: goal.target,
      current: goal.current,
      monthlyContribution: goal.monthlyContribution,
    }),
  });
  if (!res.ok) {
    throw await apiError(res, `Future You API error: ${res.status}`);
  }
  return toCustomerProfile((await res.json()) as BackendCustomer);
}

export async function deleteCurrentUserGoal(goalId: string): Promise<CustomerProfile> {
  if (!API_URL) throw new Error('VITE_API_URL is required to delete a goal.');
  const res = await fetch(apiUrl(`/me/goals/${encodeURIComponent(goalId)}`), {
    method: 'DELETE',
    headers: await authenticatedHeaders(),
  });
  if (!res.ok) {
    throw await apiError(res, `Future You API error: ${res.status}`);
  }
  return toCustomerProfile((await res.json()) as BackendCustomer);
}

export async function saveSpendingCategories(
  categories: Record<string, number>,
): Promise<CustomerProfile> {
  if (!API_URL) throw new Error('VITE_API_URL is required to save spending categories.');
  const res = await fetch(apiUrl('/me/spending-categories'), {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      ...(await authenticatedHeaders()),
    },
    body: JSON.stringify({ categories }),
  });
  if (!res.ok) {
    throw await apiError(res, `Future You API error: ${res.status}`);
  }
  return toCustomerProfile((await res.json()) as BackendCustomer);
}

export async function planAgentChanges(
  message: string,
  history: ConversationMessage[],
): Promise<ManageAgentResponse> {
  if (!API_URL) throw new Error('VITE_API_URL is required to use Manage mode.');
  const res = await fetch(apiUrl('/agent/manage'), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(await authenticatedHeaders()),
    },
    body: JSON.stringify({ message, history }),
  });
  if (!res.ok) {
    throw await apiError(res, `Future You API error: ${res.status}`);
  }
  return (await res.json()) as ManageAgentResponse;
}

export async function applyAgentChanges(proposalToken: string): Promise<CustomerProfile> {
  if (!API_URL) throw new Error('VITE_API_URL is required to apply changes.');
  const res = await fetch(apiUrl('/agent/proposals/apply'), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(await authenticatedHeaders()),
    },
    body: JSON.stringify({ proposalToken }),
  });
  if (!res.ok) {
    throw await apiError(res, `Future You API error: ${res.status}`);
  }
  return toCustomerProfile((await res.json()) as BackendCustomer);
}
