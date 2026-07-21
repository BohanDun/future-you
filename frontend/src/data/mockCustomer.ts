// Synthetic demo data for "Alex", per the project spec (section 9).
// Person 3 will replace this with a real DynamoDB-backed fetch — see
// src/lib/api.ts for the single seam where that swap happens.

export interface Goal {
  id: string;
  name: string;
  target: number;
  current: number;
  monthlyContribution: number;
}

export interface CustomerProfile {
  name: string;
  currency: string;
  balance: number;
  monthlyIncome: number;
  monthlyExpenses: number;
  monthlySavings: number;
  goals: Goal[];
  diningSpend: { month: string; amount: number }[];
  spendingCategories: { category: string; amount: number }[];
  insights: string[];
}

export const mockCustomer: CustomerProfile = {
  name: 'Alex',
  currency: 'NZD',
  balance: 8000,
  monthlyIncome: 5200,
  monthlyExpenses: 3850,
  monthlySavings: 1350,
  goals: [
    { id: 'house', name: 'House Deposit', target: 20000, current: 8000, monthlyContribution: 700 },
    { id: 'japan', name: 'Japan Holiday', target: 3000, current: 1200, monthlyContribution: 300 },
    { id: 'emergency', name: 'Emergency Fund', target: 5000, current: 3500, monthlyContribution: 350 },
  ],
  diningSpend: [
    { month: 'Apr', amount: 310 },
    { month: 'May', amount: 356 },
    { month: 'Jun', amount: 420 },
  ],
  spendingCategories: [
    { category: 'Housing', amount: 1800 },
    { category: 'Dining', amount: 420 },
    { category: 'Transport', amount: 380 },
    { category: 'Groceries', amount: 560 },
    { category: 'Subscriptions', amount: 90 },
    { category: 'Other', amount: 600 },
  ],
  insights: [
    'Your dining spending increased by approximately 18% from May to June.',
    'Housing is your largest monthly spending category at $1,800.00.',
    'You are saving approximately 26% of monthly income.',
  ],
};

export function diningInsight(profile: CustomerProfile = mockCustomer): string {
  const spend = profile.diningSpend;
  if (spend.length < 2) return 'More spending history is needed to show a trend.';
  const previous = spend[spend.length - 2];
  const latest = spend[spend.length - 1];
  const pct = Math.round(((latest.amount - previous.amount) / previous.amount) * 100);
  return `Your dining spending ${pct >= 0 ? 'increased' : 'decreased'} by approximately ${Math.abs(pct)}% from ${previous.month} to ${latest.month}.`;
}

export const suggestedQuestions = [
  'What happens if I buy a $2,000 laptop?',
  'Can I afford a $3,000 trip to Japan next year?',
  'What if I save an extra $50 per week?',
  'What if my rent increases by $100 per week?',
];
