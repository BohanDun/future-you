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
  balance: number;
  monthlyIncome: number;
  monthlyExpenses: number;
  monthlySavings: number;
  goals: Goal[];
  diningSpend: { month: string; amount: number }[];
  spendingCategories: { category: string; amount: number }[];
}

export const mockCustomer: CustomerProfile = {
  name: 'Alex',
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
};

export function diningInsight(): string {
  const spend = mockCustomer.diningSpend;
  const first = spend[0].amount;
  const last = spend[spend.length - 1].amount;
  const pct = Math.round(((last - first) / first) * 100);
  return `Your dining spending ${pct >= 0 ? 'increased' : 'decreased'} by approximately ${Math.abs(pct)}% since ${spend[0].month}.`;
}

export const suggestedQuestions = [
  'What happens if I buy a $2,000 laptop?',
  'Can I afford a trip to Japan next year?',
  'What if I save an extra $50 per week?',
  'What if my rent increases by $100 per week?',
];
