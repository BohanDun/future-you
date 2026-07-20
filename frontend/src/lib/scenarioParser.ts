// Stand-in for Amazon Bedrock's question-understanding step (spec 7.2).
// Person 4 will replace this with a real Bedrock call returning the same
// { scenarioType, amount, description } shape — see src/lib/api.ts.

import type { ParsedScenario, ScenarioType } from './financialTools';

function extractAmount(text: string): number {
  const match = text.match(/\$?\s?(\d[\d,]*(?:\.\d+)?)/);
  if (!match) return 0;
  return parseFloat(match[1].replace(/,/g, ''));
}

function extractDescription(text: string): string {
  const goalId = extractGoalId(text);
  if (goalId === 'japan_holiday') return 'Japan trip';
  if (goalId === 'emergency_fund') return 'Emergency fund';
  if (goalId === 'house_deposit') return 'House deposit';

  const stop = new Set([
    'what', 'happens', 'if', 'i', 'a', 'an', 'the', 'buy', 'to', 'can', 'afford',
    'next', 'year', 'save', 'extra', 'per', 'week', 'my', 'increases', 'by',
  ]);
  const words = text
    .replace(/[?$.,]/g, ' ')
    .split(/\s+/)
    .filter((w) => w && !stop.has(w.toLowerCase()) && Number.isNaN(Number(w)));
  const label = words.slice(-2).join(' ').trim();
  return label ? label[0].toUpperCase() + label.slice(1) : 'This scenario';
}

function extractGoalId(text: string): string | undefined {
  const lower = text.toLowerCase();
  if (/house|home|deposit/.test(lower)) return 'house_deposit';
  if (/japan|holiday|trip/.test(lower)) return 'japan_holiday';
  if (/emergency/.test(lower)) return 'emergency_fund';
  return undefined;
}

export function parseQuestion(question: string): ParsedScenario {
  const lower = question.toLowerCase();
  const amount = extractAmount(question);
  const description = extractDescription(question);

  let scenarioType: ScenarioType = 'one_off_purchase';
  if (/rent|bill|increase|per week|per month/.test(lower) && /increas/.test(lower)) {
    scenarioType = 'recurring_expense';
  } else if (/save|saving/.test(lower) && /extra|per week|per month/.test(lower)) {
    scenarioType = 'extra_savings';
  } else if (/afford|trip|holiday|goal/.test(lower)) {
    scenarioType = 'one_off_purchase';
  }

  return { scenarioType, amount, description, goalId: extractGoalId(question) };
}
