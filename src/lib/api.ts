// ---------------------------------------------------------------------------
// API layer — this is the ONE file Person 3 needs to touch to connect the
// real backend (API Gateway → Lambda → DynamoDB/Bedrock).
//
// If VITE_API_URL is set (see .env.example), askFutureYou() calls the real
// endpoint. Otherwise it falls back to a local mock pipeline (parser +
// financial tools) so the rest of the team can build and demo the UI before
// the backend is live.
// ---------------------------------------------------------------------------

import { mockCustomer } from '../data/mockCustomer';
import { parseQuestion } from './scenarioParser';
import { runSimulation, type SimulationResult } from './financialTools';

export interface AskFutureYouResponse {
  explanation: string;
  simulation: SimulationResult;
}

const API_URL = import.meta.env.VITE_API_URL as string | undefined;

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
    const res = await fetch(`${API_URL}/ask`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question }),
    });
    if (!res.ok) {
      throw new Error(`Future You API error: ${res.status}`);
    }
    return res.json();
  }

  // --- local fallback (no backend yet) ---
  await new Promise((r) => setTimeout(r, 550)); // small delay so the UI's loading state is visible
  const scenario = parseQuestion(question);
  const simulation = runSimulation(mockCustomer, scenario);
  return { explanation: explainLocally(simulation), simulation };
}

export async function fetchCustomerProfile() {
  if (API_URL) {
    const res = await fetch(`${API_URL}/customer`);
    if (!res.ok) throw new Error(`Future You API error: ${res.status}`);
    return res.json();
  }
  await new Promise((r) => setTimeout(r, 200));
  return mockCustomer;
}
