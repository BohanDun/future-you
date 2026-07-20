// Offline fallback mirroring the deterministic Python engine.
// Production and integrated local demos should call the backend API instead.

import type { CustomerProfile, Goal } from '../data/mockCustomer';

export type ScenarioType =
  | 'one_off_purchase'
  | 'recurring_expense'
  | 'extra_savings'
  | 'goal_check';

export interface ParsedScenario {
  scenarioType: ScenarioType;
  amount: number;
  description: string;
  goalId?: string;
}

export type RiskLevel = 'Low' | 'Medium' | 'High';

export interface GoalOutcome {
  goalId: string;
  goalName: string;
  monthsBefore: number;
  monthsAfter: number;
}

export interface SimulationResult {
  balanceBefore: number;
  balanceAfter: number;
  monthlySavingsBefore: number;
  monthlySavingsAfter: number;
  goals: GoalOutcome[];
  riskBefore: RiskLevel;
  riskAfter: RiskLevel;
  riskReasons: string[];
  recommendation: string;
  scenario: ParsedScenario;
}

export interface AffordabilitySummary {
  goalId: string;
  goalName: string;
  availableBalance: number;
  reserveMonths: number;
  lowRiskLimit: number;
  mediumRiskLimit: number;
  highRiskStartsAt: number | null;
  lowRiskBoundaryReasons: string[];
  mediumRiskBoundaryReasons: string[];
}

export interface FinancialHealthComponent {
  key: string;
  label: string;
  score: number;
  maxScore: number;
  summary: string;
}

export interface FinancialHealthScore {
  score: number;
  status: string;
  savingsRatePercent: number;
  reserveMonths: number;
  goalProgressPercent: number;
  components: FinancialHealthComponent[];
  nextBestAction: string;
}

export interface StressGoalImpact {
  goalId: string;
  goalName: string;
  monthsBefore: number;
  monthsAfter: number;
}

export interface StressTestResult {
  balanceBefore: number;
  balanceAfter: number;
  runwayMonthsBefore: number;
  runwayMonthsAfter: number;
  monthlyCashFlowDuringShock: number;
  riskLevel: RiskLevel;
  riskReasons: string[];
  goalImpacts: StressGoalImpact[];
  recommendation: string;
}

export interface CashTrajectoryPoint {
  month: number;
  balance: number;
  phase: 'shock' | 'recovery';
}

export interface GoalAllocation {
  goalId: string;
  goalName: string;
  monthlyContributionBefore: number;
  monthlyContributionAfter: number;
  monthsBefore: number;
  monthsAfter: number;
}

export interface GoalAllocationResult {
  priorityGoalId: string;
  requestedMonths: number;
  earliestPossibleMonths: number;
  feasible: boolean;
  monthlySavingsAvailable: number;
  allocations: GoalAllocation[];
  summary: string;
}

export interface RecoveryOption {
  title: string;
  description: string;
  impact: string;
}

const goalIdMap: Record<string, string> = {
  house_deposit: 'house',
  japan_holiday: 'japan',
  emergency_fund: 'emergency',
};

const backendGoalIdMap: Record<string, string> = {
  house: 'house_deposit',
  japan: 'japan_holiday',
  emergency: 'emergency_fund',
};

export function toBackendGoalId(goalId: string): string {
  return backendGoalIdMap[goalId] ?? goalId;
}

function matchingGoalIds(goalId: string): string[] {
  return [goalId, goalIdMap[goalId], backendGoalIdMap[goalId]].filter(
    (value): value is string => Boolean(value),
  );
}

function findGoal(profile: CustomerProfile, goalId: string): Goal | undefined {
  const candidates = matchingGoalIds(goalId);
  return profile.goals.find((goal) => candidates.includes(goal.id));
}

function roundMoney(value: number): number {
  return Math.round((value + Number.EPSILON) * 100) / 100;
}

export function calculateFinancialHealth(profile: CustomerProfile): FinancialHealthScore {
  const savingsRate = profile.monthlyIncome > 0
    ? profile.monthlySavings / profile.monthlyIncome
    : 0;
  const reserveMonths = profile.monthlyExpenses > 0
    ? profile.balance / profile.monthlyExpenses
    : 0;
  const progressValues = profile.goals
    .filter((goal) => goal.target > 0)
    .map((goal) => Math.min(Math.max(goal.current / goal.target, 0), 1));
  const averageGoalProgress = progressValues.length > 0
    ? progressValues.reduce((sum, value) => sum + value, 0) / progressValues.length
    : 0;
  const savingsScore = Math.min(Math.max(savingsRate / 0.2, 0), 1) * 40;
  const reserveScore = Math.min(Math.max(reserveMonths / 3, 0), 1) * 35;
  const goalScore = averageGoalProgress * 25;
  const score = Math.round(savingsScore + reserveScore + goalScore);
  const status = score >= 80
    ? 'Excellent'
    : score >= 65
      ? 'Strong'
      : score >= 45
        ? 'Building'
        : 'Needs attention';
  const reserveGap = Math.max(profile.monthlyExpenses * 3 - profile.balance, 0);
  let nextBestAction: string;
  if (reserveGap > 0) {
    nextBestAction = `Build another $${reserveGap.toLocaleString(undefined, {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })} in accessible reserves to cover three months of expenses.`;
  } else if (savingsRate < 0.2) {
    const monthlyGap = Math.max(profile.monthlyIncome * 0.2 - profile.monthlySavings, 0);
    nextBestAction = `Increase monthly savings by $${monthlyGap.toLocaleString(undefined, {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })} to reach a 20% savings rate.`;
  } else if (averageGoalProgress < 1) {
    nextBestAction = 'Keep the current savings plan and review goal allocations monthly.';
  } else {
    nextBestAction = 'Maintain the current plan and review it after any major life change.';
  }

  return {
    score,
    status,
    savingsRatePercent: roundMoney(savingsRate * 100),
    reserveMonths: roundMoney(reserveMonths),
    goalProgressPercent: roundMoney(averageGoalProgress * 100),
    components: [
      {
        key: 'savings_rate',
        label: 'Savings rate',
        score: roundMoney(savingsScore),
        maxScore: 40,
        summary: `${(savingsRate * 100).toFixed(1)}% of income saved`,
      },
      {
        key: 'cash_reserve',
        label: 'Cash reserve',
        score: roundMoney(reserveScore),
        maxScore: 35,
        summary: `${reserveMonths.toFixed(2)} months of expenses`,
      },
      {
        key: 'goal_progress',
        label: 'Goal progress',
        score: roundMoney(goalScore),
        maxScore: 25,
        summary: `${(averageGoalProgress * 100).toFixed(1)}% average progress`,
      },
    ],
    nextBestAction,
  };
}

export function buildCashTrajectory(
  profile: CustomerProfile,
  incomeLossMonths: number,
  unexpectedExpense: number,
  horizonMonths = 12,
): CashTrajectoryPoint[] {
  let balance = roundMoney(profile.balance - unexpectedExpense);
  const points: CashTrajectoryPoint[] = [{
    month: 0,
    balance,
    phase: incomeLossMonths > 0 ? 'shock' : 'recovery',
  }];
  for (let month = 1; month <= horizonMonths; month += 1) {
    if (month <= incomeLossMonths) {
      balance = roundMoney(balance - profile.monthlyExpenses);
    } else {
      balance = roundMoney(balance + profile.monthlySavings);
    }
    points.push({
      month,
      balance,
      phase: month <= incomeLossMonths ? 'shock' : 'recovery',
    });
  }
  return points;
}

function monthsToGoal(goal: Goal, contribution: number, current = goal.current): number {
  const remaining = goal.target - current;
  if (remaining <= 0) return 0;
  if (contribution <= 0) return Infinity;
  return Math.ceil(remaining / contribution);
}

function primaryGoalIndex(profile: CustomerProfile, scenario: ParsedScenario): number {
  if (scenario.goalId) {
    const requestedIds = matchingGoalIds(scenario.goalId);
    const requestedIndex = profile.goals.findIndex((goal) => requestedIds.includes(goal.id));
    if (requestedIndex >= 0) return requestedIndex;
  }

  const description = scenario.description.toLowerCase();
  const aliases = /japan|holiday|trip/.test(description)
    ? 'japan'
    : /emergency/.test(description)
      ? 'emergency'
      : 'house';
  const index = profile.goals.findIndex((goal) => matchingGoalIds(aliases).includes(goal.id));
  return index >= 0 ? index : 0;
}

function maxGoalDelay(goals: GoalOutcome[]): number {
  return Math.max(
    0,
    ...goals.map((goal) => {
      if (goal.monthsBefore !== Infinity && goal.monthsAfter === Infinity) return 999;
      if (goal.monthsBefore === Infinity || goal.monthsAfter === Infinity) return 0;
      return Math.max(goal.monthsAfter - goal.monthsBefore, 0);
    }),
  );
}

function assessRisk(
  cashFlowBefore: number,
  cashFlowAfter: number,
  balanceAfter: number,
  monthlyExpenses: number,
  goalDelay: number,
): { level: RiskLevel; reasons: string[] } {
  const highReasons: string[] = [];
  const mediumReasons: string[] = [];
  if (cashFlowAfter < 0) highReasons.push('Monthly cash flow becomes negative.');
  if (balanceAfter < 0) highReasons.push('Available balance becomes negative.');
  if (monthlyExpenses > 0 && balanceAfter < monthlyExpenses) {
    highReasons.push('Available balance covers less than one month of expenses.');
  }
  if (goalDelay >= 999) highReasons.push('A financial goal can no longer progress.');
  else if (goalDelay >= 6) highReasons.push(`A financial goal is delayed by ${goalDelay} months.`);
  if (highReasons.length) return { level: 'High', reasons: highReasons };

  if (monthlyExpenses > 0 && balanceAfter < monthlyExpenses * 2) {
    mediumReasons.push('Available balance covers less than two months of expenses.');
  }
  if (cashFlowBefore > 0 && cashFlowAfter <= cashFlowBefore * 0.5) {
    mediumReasons.push('Monthly cash flow falls by at least 50%.');
  }
  if (goalDelay >= 2) mediumReasons.push(`A financial goal is delayed by ${goalDelay} months.`);
  if (mediumReasons.length) return { level: 'Medium', reasons: mediumReasons };
  return { level: 'Low', reasons: ['Cash flow and financial buffers remain healthy.'] };
}

function recommendation(
  scenario: ParsedScenario,
  riskAfter: RiskLevel,
  goalDelay: number,
): string {
  if (scenario.scenarioType === 'one_off_purchase') {
    if (riskAfter === 'Low' && goalDelay === 0) {
      return 'This purchase fits within the current plan.';
    }
    const weeklyRecovery = Math.ceil((scenario.amount / 52) / 5) * 5;
    return `Reducing discretionary spending by $${weeklyRecovery} per week could help recover the goal delay.`;
  }
  if (scenario.scenarioType === 'recurring_expense') {
    return 'Review recurring expenses before committing to the increase.';
  }
  return 'Continue the additional savings plan.';
}

function makeResult(
  profile: CustomerProfile,
  scenario: ParsedScenario,
  balanceAfter: number,
  cashFlowAfter: number,
  goals: GoalOutcome[],
): SimulationResult {
  const delay = maxGoalDelay(goals);
  const riskBefore = assessRisk(
    profile.monthlySavings,
    profile.monthlySavings,
    profile.balance,
    profile.monthlyExpenses,
    0,
  );
  const riskAfter = assessRisk(
    profile.monthlySavings,
    cashFlowAfter,
    balanceAfter,
    profile.monthlyExpenses,
    delay,
  );
  return {
    balanceBefore: profile.balance,
    balanceAfter: roundMoney(balanceAfter),
    monthlySavingsBefore: profile.monthlySavings,
    monthlySavingsAfter: roundMoney(cashFlowAfter),
    goals,
    riskBefore: riskBefore.level,
    riskAfter: riskAfter.level,
    riskReasons: riskAfter.reasons,
    recommendation: recommendation(scenario, riskAfter.level, delay),
    scenario,
  };
}

function simulateOneOffPurchase(
  profile: CustomerProfile,
  scenario: ParsedScenario,
): SimulationResult {
  const primaryIndex = primaryGoalIndex(profile, scenario);
  const goals = profile.goals.map((goal, index) => {
    const currentAfter = index === primaryIndex
      ? Math.max(goal.current - scenario.amount, 0)
      : goal.current;
    return {
      goalId: goal.id,
      goalName: goal.name,
      monthsBefore: monthsToGoal(goal, goal.monthlyContribution),
      monthsAfter: monthsToGoal(goal, goal.monthlyContribution, currentAfter),
    };
  });
  return makeResult(
    profile,
    scenario,
    profile.balance - scenario.amount,
    profile.monthlySavings,
    goals,
  );
}

function simulateRecurringExpense(
  profile: CustomerProfile,
  scenario: ParsedScenario,
): SimulationResult {
  const monthlyCost = roundMoney((scenario.amount * 52) / 12);
  const cashFlowAfter = roundMoney(profile.monthlySavings - monthlyCost);
  const totalContributions = profile.goals.reduce(
    (total, goal) => total + goal.monthlyContribution,
    0,
  );
  const availableForGoals = Math.max(totalContributions - monthlyCost, 0);
  const scale = totalContributions > 0 ? availableForGoals / totalContributions : 0;
  const goals = profile.goals.map((goal) => ({
    goalId: goal.id,
    goalName: goal.name,
    monthsBefore: monthsToGoal(goal, goal.monthlyContribution),
    monthsAfter: monthsToGoal(goal, goal.monthlyContribution * scale),
  }));
  return makeResult(profile, scenario, profile.balance, cashFlowAfter, goals);
}

function simulateExtraSavings(
  profile: CustomerProfile,
  scenario: ParsedScenario,
): SimulationResult {
  const extraMonthly = roundMoney((scenario.amount * 52) / 12);
  const primaryIndex = primaryGoalIndex(profile, scenario);
  const goals = profile.goals.map((goal, index) => {
    const contribution = goal.monthlyContribution + (index === primaryIndex ? extraMonthly : 0);
    return {
      goalId: goal.id,
      goalName: goal.name,
      monthsBefore: monthsToGoal(goal, goal.monthlyContribution),
      monthsAfter: monthsToGoal(goal, contribution),
    };
  });
  return makeResult(profile, scenario, profile.balance, profile.monthlySavings, goals);
}

export function runSimulation(
  profile: CustomerProfile,
  scenario: ParsedScenario,
): SimulationResult {
  switch (scenario.scenarioType) {
    case 'one_off_purchase':
      return simulateOneOffPurchase(profile, scenario);
    case 'recurring_expense':
      return simulateRecurringExpense(profile, scenario);
    case 'extra_savings':
      return simulateExtraSavings(profile, scenario);
    default:
      return simulateOneOffPurchase(profile, scenario);
  }
}

const riskRank: Record<RiskLevel, number> = { Low: 0, Medium: 1, High: 2 };

function purchaseResult(
  profile: CustomerProfile,
  goal: Goal,
  amount: number,
): SimulationResult {
  return runSimulation(profile, {
    scenarioType: 'one_off_purchase',
    amount,
    description: goal.name,
    goalId: goal.id,
  });
}

function maxPurchaseForRisk(
  profile: CustomerProfile,
  goal: Goal,
  maximumRisk: RiskLevel,
): number {
  let lowCents = 0;
  let highCents = Math.round(profile.balance * 100);
  let bestCents = 0;
  while (lowCents <= highCents) {
    const midpoint = Math.floor((lowCents + highCents) / 2);
    const result = purchaseResult(profile, goal, midpoint / 100);
    if (riskRank[result.riskAfter] <= riskRank[maximumRisk]) {
      bestCents = midpoint;
      lowCents = midpoint + 1;
    } else {
      highCents = midpoint - 1;
    }
  }
  return bestCents / 100;
}

export function calculateAffordability(
  profile: CustomerProfile,
  goalId: string,
): AffordabilitySummary {
  const goal = findGoal(profile, goalId) ?? profile.goals[0];
  const lowRiskLimit = maxPurchaseForRisk(profile, goal, 'Low');
  const mediumRiskLimit = maxPurchaseForRisk(profile, goal, 'Medium');
  const nextLow = Math.min(lowRiskLimit + 0.01, profile.balance);
  const nextMedium = Math.min(mediumRiskLimit + 0.01, profile.balance);
  return {
    goalId: goal.id,
    goalName: goal.name,
    availableBalance: profile.balance,
    reserveMonths: profile.monthlyExpenses > 0
      ? roundMoney(profile.balance / profile.monthlyExpenses)
      : 0,
    lowRiskLimit,
    mediumRiskLimit,
    highRiskStartsAt: mediumRiskLimit < profile.balance ? roundMoney(nextMedium) : null,
    lowRiskBoundaryReasons: lowRiskLimit < profile.balance
      ? purchaseResult(profile, goal, nextLow).riskReasons
      : [],
    mediumRiskBoundaryReasons: mediumRiskLimit < profile.balance
      ? purchaseResult(profile, goal, nextMedium).riskReasons
      : [],
  };
}

export function calculateStressTest(
  profile: CustomerProfile,
  incomeLossMonths: number,
  unexpectedExpense: number,
): StressTestResult {
  const shockCost = profile.monthlyExpenses * incomeLossMonths + unexpectedExpense;
  const balanceAfter = roundMoney(profile.balance - shockCost);
  const cashFlowDuringShock = incomeLossMonths > 0
    ? -profile.monthlyExpenses
    : profile.monthlySavings;
  const risk = assessRisk(
    profile.monthlySavings,
    cashFlowDuringShock,
    balanceAfter,
    profile.monthlyExpenses,
    incomeLossMonths,
  );
  return {
    balanceBefore: profile.balance,
    balanceAfter,
    runwayMonthsBefore: profile.monthlyExpenses > 0
      ? roundMoney(profile.balance / profile.monthlyExpenses)
      : 0,
    runwayMonthsAfter: profile.monthlyExpenses > 0
      ? roundMoney(Math.max(balanceAfter, 0) / profile.monthlyExpenses)
      : 0,
    monthlyCashFlowDuringShock: cashFlowDuringShock,
    riskLevel: risk.level,
    riskReasons: risk.reasons,
    goalImpacts: profile.goals.map((goal) => ({
      goalId: goal.id,
      goalName: goal.name,
      monthsBefore: monthsToGoal(goal, goal.monthlyContribution),
      monthsAfter: monthsToGoal(goal, goal.monthlyContribution) + incomeLossMonths,
    })),
    recommendation: risk.level === 'High'
      ? 'Protect essential expenses and pause discretionary goal contributions during the shock.'
      : 'Rebuild the emergency buffer before increasing discretionary spending.',
  };
}

export function calculateGoalAllocation(
  profile: CustomerProfile,
  priorityGoalId: string,
  targetMonths: number,
): GoalAllocationResult {
  const priority = findGoal(profile, priorityGoalId) ?? profile.goals[0];
  const remaining = Math.max(priority.target - priority.current, 0);
  const earliestPossibleMonths = profile.monthlySavings > 0
    ? Math.ceil(remaining / profile.monthlySavings)
    : Infinity;
  const required = Math.ceil((remaining / targetMonths) * 100) / 100;
  const feasible = required <= profile.monthlySavings;
  const priorityAllocation = Math.min(required, profile.monthlySavings);
  const remainingBudget = roundMoney(profile.monthlySavings - priorityAllocation);
  const otherGoals = profile.goals.filter((goal) => goal.id !== priority.id);
  const otherTotal = otherGoals.reduce((total, goal) => total + goal.monthlyContribution, 0);
  const values = new Map<string, number>([[priority.id, priorityAllocation]]);
  let allocated = 0;
  otherGoals.forEach((goal, index) => {
    const value = index === otherGoals.length - 1
      ? roundMoney(remainingBudget - allocated)
      : roundMoney(otherTotal > 0
        ? remainingBudget * goal.monthlyContribution / otherTotal
        : 0);
    values.set(goal.id, value);
    allocated = roundMoney(allocated + value);
  });
  const allocations = profile.goals.map((goal) => {
    const contributionAfter = values.get(goal.id) ?? 0;
    return {
      goalId: goal.id,
      goalName: goal.name,
      monthlyContributionBefore: goal.monthlyContribution,
      monthlyContributionAfter: contributionAfter,
      monthsBefore: monthsToGoal(goal, goal.monthlyContribution),
      monthsAfter: monthsToGoal(goal, contributionAfter),
    };
  });
  return {
    priorityGoalId: priority.id,
    requestedMonths: targetMonths,
    earliestPossibleMonths,
    feasible,
    monthlySavingsAvailable: profile.monthlySavings,
    allocations,
    summary: feasible
      ? `Allocate $${priorityAllocation.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })} per month to ${priority.name} and distribute the remaining $${remainingBudget.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })} across other goals.`
      : `The requested deadline is not feasible. The earliest possible timeline is ${earliestPossibleMonths} months using all available monthly savings.`,
  };
}

function flexibleSpendingPlan(profile: CustomerProfile, weeklyAmount: number): string {
  const flexible = profile.spendingCategories.filter(
    (item) => !['Housing', 'Groceries'].includes(item.category),
  );
  const total = flexible.reduce((sum, item) => sum + item.amount, 0);
  if (total <= 0 || weeklyAmount <= 0) return 'Review flexible spending categories.';
  const parts = flexible
    .map((item) => ({
      category: item.category,
      weekly: Math.max(1, Math.round(weeklyAmount * item.amount / total)),
    }))
    .filter((item) => item.weekly > 0)
    .slice(0, 4)
    .map((item) => `$${item.weekly}/week from ${item.category}`);
  return parts.join(', ');
}

export function buildRecoveryOptions(
  profile: CustomerProfile,
  result: SimulationResult,
): RecoveryOption[] {
  const amount = result.scenario.amount;
  const targetGoal = result.goals.find(
    (goal) => matchingGoalIds(result.scenario.goalId ?? '').includes(goal.goalId),
  ) ?? result.goals.find((goal) => goal.monthsBefore !== goal.monthsAfter) ?? result.goals[0];

  if (result.scenario.scenarioType === 'one_off_purchase') {
    const affordability = calculateAffordability(profile, targetGoal?.goalId ?? profile.goals[0].id);
    const gap = Math.max(amount - affordability.lowRiskLimit, 0);
    const waitMonths = profile.monthlySavings > 0 ? Math.ceil(gap / profile.monthlySavings) : 0;
    const weeklyRecovery = Math.ceil((amount / 52) / 5) * 5;
    return [
      {
        title: 'Stay Low Risk',
        description: `Keep the purchase at or below $${affordability.lowRiskLimit.toLocaleString()}.`,
        impact: 'Preserves the current financial buffer and Low risk rating.',
      },
      {
        title: 'Wait Before Buying',
        description: waitMonths > 0
          ? `Wait approximately ${waitMonths} month${waitMonths === 1 ? '' : 's'} before making the purchase.`
          : 'The purchase already fits within the Low risk range.',
        impact: 'Builds the cash buffer before the balance is reduced.',
      },
      {
        title: 'Recover Through Spending',
        description: flexibleSpendingPlan(profile, weeklyRecovery),
        impact: `Redirect approximately $${weeklyRecovery}/week for one year.`,
      },
    ];
  }

  if (result.scenario.scenarioType === 'recurring_expense') {
    return [
      {
        title: 'Fully Offset the Increase',
        description: flexibleSpendingPlan(profile, amount),
        impact: `Protects approximately $${amount}/week of cash flow.`,
      },
      {
        title: 'Negotiate the Change',
        description: `Keep the increase below $${Math.max(Math.floor(amount / 2), 1)}/week.`,
        impact: 'Reduces the delay across every active goal.',
      },
      {
        title: 'Pause and Review',
        description: 'Review subscriptions and discretionary categories before committing.',
        impact: 'Prevents a permanent High risk cash-flow change.',
      },
    ];
  }

  return [
    {
      title: 'Fund the Increase',
      description: flexibleSpendingPlan(profile, amount),
      impact: 'Creates a clear source for the additional goal contribution.',
    },
    {
      title: 'Reallocate Existing Savings',
      description: 'Use Goal Optimizer to rebalance the existing monthly savings budget.',
      impact: 'Avoids creating contributions above available monthly cash flow.',
    },
    {
      title: 'Automate the Transfer',
      description: `Schedule a $${amount}/week transfer immediately after income arrives.`,
      impact: 'Makes the accelerated goal plan consistent and measurable.',
    },
  ];
}
