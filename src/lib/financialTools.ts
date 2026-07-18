// Financial calculation tools — TypeScript port of spec section 8.
//
// IMPORTANT: this file exists so the frontend can demo end-to-end before
// Person 3's backend and Person 2's Python tools are live. Once the real
// API is ready, src/lib/api.ts should call it instead and this file can be
// deleted or kept only for local/offline dev. The math here intentionally
// mirrors the spec exactly so behaviour matches the real backend.

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
  recommendation: string;
  scenario: ParsedScenario;
}

// 8.2 Goal Completion Tool
function monthsToGoal(goal: Goal, monthlyContribution: number): number {
  const remaining = goal.target - goal.current;
  if (remaining <= 0) return 0;
  if (monthlyContribution <= 0) return Infinity;
  return Math.ceil(remaining / monthlyContribution);
}

// 8.6 Risk Tool — simple rule-based, calculated by code (not the AI)
function assessRisk(monthlySavings: number, emergencyMonths: number, maxGoalDelay: number): RiskLevel {
  if (monthlySavings < 0 || emergencyMonths < 1) return 'High';
  if (maxGoalDelay >= 6) return 'High';
  if (maxGoalDelay >= 2 || emergencyMonths < 2) return 'Medium';
  const savingsDropRatio = monthlySavings; // placeholder hook for future rules
  return savingsDropRatio < 0 ? 'Medium' : 'Low';
}

function emergencyFundMonths(profile: CustomerProfile, balance: number): number {
  const emergencyGoal = profile.goals.find((g) => g.id === 'emergency');
  const emergencyTarget = emergencyGoal ? emergencyGoal.target : profile.monthlyExpenses * 3;
  return profile.monthlyExpenses > 0 ? Math.min(balance, emergencyTarget) / (profile.monthlyExpenses / 3) : 0;
}

function goalOutcomes(
  profile: CustomerProfile,
  monthlyContributionDelta: number,
): GoalOutcome[] {
  return profile.goals.map((g) => {
    const before = monthsToGoal(g, g.monthlyContribution);
    const after = monthsToGoal(g, Math.max(0, g.monthlyContribution + monthlyContributionDelta));
    return { goalId: g.id, goalName: g.name, monthsBefore: before, monthsAfter: after };
  });
}

function buildRecommendation(result: Omit<SimulationResult, 'recommendation'>): string {
  const worstDelay = Math.max(
    0,
    ...result.goals.map((g) => (g.monthsAfter === Infinity ? 0 : g.monthsAfter - g.monthsBefore)),
  );
  if (result.riskAfter === 'Low' && worstDelay === 0) {
    return 'This fits comfortably within your current plan — no adjustment needed.';
  }
  if (worstDelay > 0) {
    return 'Reducing dining spending by about $40 per week could help recover most of the delay.';
  }
  return 'Keep an eye on your monthly cash flow over the next few months.';
}

// 8.3 One-Time Purchase Tool
function simulateOneOffPurchase(profile: CustomerProfile, amount: number): SimulationResult {
  const balanceBefore = profile.balance;
  const balanceAfter = balanceBefore - amount;
  const monthsToRecover = Math.max(1, Math.ceil(amount / Math.max(profile.monthlySavings, 1)));
  // A large one-off purchase temporarily slows the goal it's assumed to compete with (house deposit)
  // by pausing contributions for the months needed to recover the spend, approximated here as a
  // pro-rated contribution dip spread over 3 months for the demo.
  const contributionDip = Math.min(profile.goals[0].monthlyContribution, amount / 3);
  const goals = profile.goals.map((g, idx) => {
    const before = monthsToGoal(g, g.monthlyContribution);
    const dip = idx === 0 ? contributionDip : 0;
    const after = monthsToGoal(g, Math.max(0, g.monthlyContribution - dip / 3));
    return { goalId: g.id, goalName: g.name, monthsBefore: before, monthsAfter: after };
  });

  const emergencyBefore = emergencyFundMonths(profile, balanceBefore);
  const emergencyAfter = emergencyFundMonths(profile, balanceAfter);
  const maxDelayBefore = 0;
  const maxDelayAfter = Math.max(...goals.map((g) => (g.monthsAfter === Infinity ? 0 : g.monthsAfter - g.monthsBefore)));

  const riskBefore = assessRisk(profile.monthlySavings, emergencyBefore, maxDelayBefore);
  const riskAfter = assessRisk(profile.monthlySavings, emergencyAfter, maxDelayAfter);

  const base = {
    balanceBefore,
    balanceAfter,
    monthlySavingsBefore: profile.monthlySavings,
    monthlySavingsAfter: profile.monthlySavings,
    goals,
    riskBefore,
    riskAfter,
    scenario: { scenarioType: 'one_off_purchase' as ScenarioType, amount, description: 'Purchase' },
  };
  return { ...base, recommendation: buildRecommendation(base) };
}

// 8.4 Recurring Expense Tool
function simulateRecurringExpense(profile: CustomerProfile, weeklyIncrease: number): SimulationResult {
  const monthlyExtraCost = (weeklyIncrease * 52) / 12;
  const monthlySavingsAfter = profile.monthlySavings - monthlyExtraCost;
  const goals = goalOutcomes(profile, -monthlyExtraCost * 0.3); // spread impact across goal contributions
  const emergencyBefore = emergencyFundMonths(profile, profile.balance);
  const maxDelayAfter = Math.max(
    ...goals.map((g) => (g.monthsAfter === Infinity ? 0 : g.monthsAfter - g.monthsBefore)),
  );
  const riskBefore = assessRisk(profile.monthlySavings, emergencyBefore, 0);
  const riskAfter = assessRisk(monthlySavingsAfter, emergencyBefore, maxDelayAfter);

  const base = {
    balanceBefore: profile.balance,
    balanceAfter: profile.balance,
    monthlySavingsBefore: profile.monthlySavings,
    monthlySavingsAfter,
    goals,
    riskBefore,
    riskAfter,
    scenario: { scenarioType: 'recurring_expense' as ScenarioType, amount: weeklyIncrease, description: 'Rent increase' },
  };
  return { ...base, recommendation: buildRecommendation(base) };
}

// 8.5 Extra Savings Tool
function simulateExtraSavings(profile: CustomerProfile, weeklyAmount: number): SimulationResult {
  const extraMonthlySavings = (weeklyAmount * 52) / 12;
  const monthlySavingsAfter = profile.monthlySavings + extraMonthlySavings;
  const goals = goalOutcomes(profile, extraMonthlySavings * 0.5);
  const emergencyBefore = emergencyFundMonths(profile, profile.balance);
  const riskBefore = assessRisk(profile.monthlySavings, emergencyBefore, 0);
  const riskAfter = assessRisk(monthlySavingsAfter, emergencyBefore, 0);

  const base = {
    balanceBefore: profile.balance,
    balanceAfter: profile.balance,
    monthlySavingsBefore: profile.monthlySavings,
    monthlySavingsAfter,
    goals,
    riskBefore,
    riskAfter,
    scenario: { scenarioType: 'extra_savings' as ScenarioType, amount: weeklyAmount, description: 'Extra savings' },
  };
  return { ...base, recommendation: buildRecommendation(base) };
}

export function runSimulation(profile: CustomerProfile, scenario: ParsedScenario): SimulationResult {
  switch (scenario.scenarioType) {
    case 'one_off_purchase':
      return simulateOneOffPurchase(profile, scenario.amount);
    case 'recurring_expense':
      return simulateRecurringExpense(profile, scenario.amount);
    case 'extra_savings':
      return simulateExtraSavings(profile, scenario.amount);
    default:
      return simulateOneOffPurchase(profile, scenario.amount);
  }
}
