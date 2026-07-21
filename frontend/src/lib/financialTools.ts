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
  horizonMonths?: number;
  timingLabel?: string;
}

export type RiskLevel = 'Low' | 'Medium' | 'High';

export interface GoalOutcome {
  goalId: string;
  goalName: string;
  monthsBefore: number;
  monthsAfter: number;
  currentAtEvent?: number;
}

export interface SimulationResult {
  balanceBefore: number;
  balanceAfter: number;
  balanceAtEventBefore?: number;
  monthlySavingsBefore: number;
  monthlySavingsAfter: number;
  goals: GoalOutcome[];
  riskBefore: RiskLevel;
  riskAfter: RiskLevel;
  riskReasons: string[];
  recommendation: string;
  scenario: ParsedScenario;
  goalContributionsByEvent?: number;
  fundedFromGoal?: number;
  fundedFromBalance?: number;
  eventRisk?: RiskLevel;
}

function roundMoney(value: number): number {
  return Math.round((value + Number.EPSILON) * 100) / 100;
}

function monthsToGoal(goal: Goal, contribution: number, current = goal.current): number {
  const remaining = goal.target - current;
  if (remaining <= 0) return 0;
  if (contribution <= 0) return Infinity;
  return Math.ceil(remaining / contribution);
}

function primaryGoalIndex(
  profile: CustomerProfile,
  scenario: ParsedScenario,
  useDefault = true,
): number {
  const goalIdMap: Record<string, string> = {
    house_deposit: 'house',
    japan_holiday: 'japan',
    emergency_fund: 'emergency',
  };
  const requestedId = scenario.goalId ? (goalIdMap[scenario.goalId] ?? scenario.goalId) : undefined;
  if (requestedId) {
    const requestedIndex = profile.goals.findIndex((goal) => goal.id === requestedId);
    if (requestedIndex >= 0) return requestedIndex;
  }

  const description = scenario.description.toLowerCase();
  const index = profile.goals.findIndex((goal) => (
    description.includes(goal.name.toLowerCase())
    || goal.name.toLowerCase().split(/\s+/).some((word) => (
      word.length >= 4 && description.includes(word)
    ))
  ));
  return index >= 0 ? index : useDefault && profile.goals.length ? 0 : -1;
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
  projection?: {
    balanceAtEventBefore: number;
    goalContributionsByEvent: number;
    fundedFromGoal: number;
    fundedFromBalance: number;
  },
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
    ...projection,
  };
}

function simulateOneOffPurchase(
  profile: CustomerProfile,
  scenario: ParsedScenario,
): SimulationResult {
  const horizon = scenario.horizonMonths ?? 0;
  const projectedGoals = profile.goals.map((goal) => goal.current);
  let projectedBalance = profile.balance;
  let totalContributions = 0;
  for (let month = 0; month < horizon; month += 1) {
    projectedBalance += profile.monthlySavings;
    profile.goals.forEach((goal, index) => {
      const remaining = Math.max(goal.target - projectedGoals[index], 0);
      const contribution = Math.min(goal.monthlyContribution, remaining);
      projectedGoals[index] += contribution;
      projectedBalance -= contribution;
      totalContributions += contribution;
    });
  }
  const primaryIndex = primaryGoalIndex(profile, scenario, false);
  const fundedFromGoal = primaryIndex >= 0
    ? Math.min(projectedGoals[primaryIndex], scenario.amount)
    : 0;
  const fundedFromBalance = scenario.amount - fundedFromGoal;
  const goals = profile.goals.map((goal, index) => ({
    goalId: goal.id,
    goalName: goal.name,
    monthsBefore: monthsToGoal(goal, goal.monthlyContribution),
    monthsAfter: monthsToGoal(goal, goal.monthlyContribution),
    currentAtEvent: projectedGoals[index],
  }));
  return makeResult(
    profile,
    scenario,
    projectedBalance - fundedFromBalance,
    profile.monthlySavings,
    goals,
    {
      balanceAtEventBefore: projectedBalance,
      goalContributionsByEvent: totalContributions,
      fundedFromGoal,
      fundedFromBalance,
    },
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
