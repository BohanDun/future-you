import { useMemo, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Card,
  Chip,
  Divider,
  MenuItem,
  Skeleton,
  Slider,
  Stack,
  Tab,
  Tabs,
  TextField,
  Typography,
} from '@mui/material';
import { colors, numericFont } from '../../theme/theme';
import type { CustomerProfile, Goal } from '../../data/mockCustomer';
import {
  calculateAffordability,
  calculateGoalAllocation,
  calculateStressTest,
  runSimulation,
  type AffordabilitySummary,
  type GoalAllocationResult,
  type SimulationResult,
  type StressTestResult,
} from '../../lib/financialTools';
import {
  fetchAffordability,
  optimizeGoalPlan,
  runFinancialStressTest,
} from '../../lib/api';
import { formatCurrency, formatMonths } from '../../lib/format';
import { RiskBadge } from '../Simulation/RiskBadge';

interface DecisionLabProps {
  profile: CustomerProfile;
  onAsk: (question: string) => void;
}

interface SavedScenario {
  id: string;
  amount: number;
  goalName: string;
  result: SimulationResult;
}

function GoalSelect({
  goals,
  value,
  onChange,
  label,
}: {
  goals: Goal[];
  value: string;
  onChange: (goalId: string) => void;
  label: string;
}) {
  return (
    <TextField
      select
      fullWidth
      size="small"
      label={label}
      value={value}
      onChange={(event) => onChange(event.target.value)}
    >
      {goals.map((goal) => (
        <MenuItem key={goal.id} value={goal.id}>{goal.name}</MenuItem>
      ))}
    </TextField>
  );
}

function RangeMeter({
  affordability,
  amount,
}: {
  affordability: AffordabilitySummary;
  amount: number;
}) {
  const total = Math.max(affordability.availableBalance, 1);
  const lowWidth = Math.min(affordability.lowRiskLimit / total * 100, 100);
  const mediumWidth = Math.max(
    Math.min(affordability.mediumRiskLimit / total * 100, 100) - lowWidth,
    0,
  );
  const highWidth = Math.max(100 - lowWidth - mediumWidth, 0);
  const marker = Math.min(Math.max(amount / total * 100, 0), 100);

  return (
    <Stack spacing={1}>
      <Box sx={{ position: 'relative', pt: 1.5 }}>
        <Box
          sx={{
            position: 'absolute',
            left: `${marker}%`,
            top: 0,
            transform: 'translateX(-50%)',
            width: 2,
            height: 22,
            bgcolor: colors.ink,
            borderRadius: 2,
            zIndex: 1,
          }}
        />
        <Stack direction="row" sx={{ height: 10, borderRadius: 5, overflow: 'hidden' }}>
          <Box sx={{ width: `${lowWidth}%`, bgcolor: colors.riskLow }} />
          <Box sx={{ width: `${mediumWidth}%`, bgcolor: colors.riskMedium }} />
          <Box sx={{ width: `${highWidth}%`, bgcolor: colors.riskHigh }} />
        </Stack>
      </Box>
      <Stack direction="row" justifyContent="space-between">
        <Typography variant="caption">Low to {formatCurrency(affordability.lowRiskLimit)}</Typography>
        <Typography variant="caption">Medium to {formatCurrency(affordability.mediumRiskLimit)}</Typography>
        <Typography variant="caption">High</Typography>
      </Stack>
    </Stack>
  );
}

function AffordabilityTab({ profile, onAsk }: DecisionLabProps) {
  const firstGoal = profile.goals[0];
  const [goalId, setGoalId] = useState(firstGoal.id);
  const [amount, setAmount] = useState(Math.min(2000, profile.balance));
  const [affordability, setAffordability] = useState<AffordabilitySummary>(() =>
    calculateAffordability(profile, firstGoal.id),
  );
  const [loading, setLoading] = useState(false);
  const [saved, setSaved] = useState<SavedScenario[]>([]);
  const selectedGoal = profile.goals.find((goal) => goal.id === goalId) ?? firstGoal;
  const result = useMemo(
    () => runSimulation(profile, {
      scenarioType: 'one_off_purchase',
      amount,
      description: selectedGoal.name,
      goalId,
    }),
    [amount, goalId, profile, selectedGoal.name],
  );
  const targetOutcome = result.goals.find(
    (goal) => goal.goalId === goalId,
  ) ?? result.goals.find((goal) => goal.monthsBefore !== goal.monthsAfter) ?? result.goals[0];

  function loadAffordability(nextGoalId: string) {
    setGoalId(nextGoalId);
    setLoading(true);
    fetchAffordability(profile, nextGoalId)
      .then(setAffordability)
      .catch(() => setAffordability(calculateAffordability(profile, nextGoalId)))
      .finally(() => setLoading(false));
  }

  function askScenario() {
    const formatted = amount.toLocaleString();
    const question = selectedGoal.name === 'Japan Holiday'
      ? `Can I afford a $${formatted} trip to Japan?`
      : `What happens if I make a $${formatted} purchase using my ${selectedGoal.name}?`;
    onAsk(question);
  }

  function saveScenario() {
    const key = `${goalId}-${amount}`;
    setSaved((current) => {
      const withoutDuplicate = current.filter((item) => item.id !== key);
      return [
        ...withoutDuplicate,
        { id: key, amount, goalName: selectedGoal.name, result },
      ].slice(-3);
    });
  }

  return (
    <Stack spacing={2.25}>
      <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.5}>
        <GoalSelect
          goals={profile.goals}
          value={goalId}
          onChange={loadAffordability}
          label="Funding source"
        />
        <Box sx={{ minWidth: 150 }}>
          <Typography variant="caption" sx={{ color: colors.inkSoft }}>Purchase amount</Typography>
          <Typography sx={{ fontFamily: numericFont, fontSize: '1.4rem' }}>
            {formatCurrency(amount)}
          </Typography>
        </Box>
      </Stack>

      <Slider
        value={amount}
        min={0}
        max={profile.balance}
        step={100}
        valueLabelDisplay="auto"
        valueLabelFormat={(value) => formatCurrency(value)}
        onChange={(_, value) => setAmount(value as number)}
        aria-label="Purchase amount"
      />

      {loading ? <Skeleton height={58} /> : <RangeMeter affordability={affordability} amount={amount} />}

      <Stack direction="row" justifyContent="space-between" alignItems="center">
        <Stack>
          <Typography variant="caption" sx={{ color: colors.inkSoft }}>Selected outcome</Typography>
          <Typography variant="body2">
            {targetOutcome.goalName}: {formatMonths(targetOutcome.monthsBefore)} → {formatMonths(targetOutcome.monthsAfter)}
          </Typography>
        </Stack>
        <RiskBadge level={result.riskAfter} />
      </Stack>

      <Alert severity={result.riskAfter === 'High' ? 'error' : result.riskAfter === 'Medium' ? 'warning' : 'success'}>
        {result.riskReasons.join(' ')}
      </Alert>

      <Stack direction="row" spacing={1}>
        <Button variant="contained" onClick={askScenario} disabled={amount <= 0}>
          Ask Future You
        </Button>
        <Button variant="outlined" onClick={saveScenario}>Save scenario</Button>
      </Stack>

      <Divider />
      <Stack spacing={1}>
        <Stack direction="row" justifyContent="space-between" alignItems="center">
          <Typography variant="h6" sx={{ color: colors.inkSoft }}>Scenario comparison</Typography>
          {saved.length > 0 && (
            <Button size="small" onClick={() => setSaved([])}>Clear</Button>
          )}
        </Stack>
        {saved.length === 0 ? (
          <Typography variant="body2" sx={{ color: colors.inkSoft }}>
            Save up to three amounts to compare balance, timeline and risk.
          </Typography>
        ) : saved.map((scenario) => {
          const changedGoal = scenario.result.goals.find(
            (goal) => goal.monthsBefore !== goal.monthsAfter,
          ) ?? scenario.result.goals[0];
          return (
            <Stack
              key={scenario.id}
              direction="row"
              justifyContent="space-between"
              alignItems="center"
              sx={{ border: `1px solid ${colors.line}`, borderRadius: 2, p: 1.25 }}
            >
              <Stack>
                <Typography variant="body2" fontWeight={600}>
                  {formatCurrency(scenario.amount)} | {scenario.goalName}
                </Typography>
                <Typography variant="caption" sx={{ color: colors.inkSoft }}>
                  Balance {formatCurrency(scenario.result.balanceAfter)} | {changedGoal.goalName} {formatMonths(changedGoal.monthsAfter)}
                </Typography>
              </Stack>
              <RiskBadge level={scenario.result.riskAfter} />
            </Stack>
          );
        })}
      </Stack>
    </Stack>
  );
}

const stressPresets = [
  { label: '$2,500 emergency', incomeLossMonths: 0, unexpectedExpense: 2500 },
  { label: '1 month income loss', incomeLossMonths: 1, unexpectedExpense: 0 },
  { label: '2 months income loss', incomeLossMonths: 2, unexpectedExpense: 0 },
];

function StressTestTab({ profile }: { profile: CustomerProfile }) {
  const initial = stressPresets[0];
  const [selected, setSelected] = useState(initial.label);
  const [result, setResult] = useState<StressTestResult>(() =>
    calculateStressTest(profile, initial.incomeLossMonths, initial.unexpectedExpense),
  );
  const [loading, setLoading] = useState(false);

  function runPreset(preset: typeof stressPresets[number]) {
    setSelected(preset.label);
    setLoading(true);
    runFinancialStressTest(
      profile,
      preset.incomeLossMonths,
      preset.unexpectedExpense,
    )
      .then(setResult)
      .catch(() => setResult(calculateStressTest(
        profile,
        preset.incomeLossMonths,
        preset.unexpectedExpense,
      )))
      .finally(() => setLoading(false));
  }

  return (
    <Stack spacing={2}>
      <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap">
        {stressPresets.map((preset) => (
          <Chip
            key={preset.label}
            label={preset.label}
            clickable
            color={selected === preset.label ? 'primary' : 'default'}
            onClick={() => runPreset(preset)}
          />
        ))}
      </Stack>
      {loading ? <Skeleton height={150} /> : (
        <>
          <Stack direction="row" spacing={3}>
            <Box>
              <Typography variant="caption" sx={{ color: colors.inkSoft }}>Emergency runway</Typography>
              <Typography sx={{ fontFamily: numericFont, fontSize: '1.4rem' }}>
                {result.runwayMonthsBefore} → {result.runwayMonthsAfter} months
              </Typography>
            </Box>
            <Box>
              <Typography variant="caption" sx={{ color: colors.inkSoft }}>Balance after shock</Typography>
              <Typography sx={{ fontFamily: numericFont, fontSize: '1.4rem' }}>
                {formatCurrency(result.balanceAfter)}
              </Typography>
            </Box>
          </Stack>
          <RiskBadge level={result.riskLevel} />
          <Alert severity={result.riskLevel === 'High' ? 'error' : 'warning'}>
            {result.riskReasons.join(' ')} {result.recommendation}
          </Alert>
          <Stack spacing={0.5}>
            {result.goalImpacts.map((goal) => (
              <Stack key={goal.goalId} direction="row" justifyContent="space-between">
                <Typography variant="body2">{goal.goalName}</Typography>
                <Typography variant="body2" sx={{ fontFamily: numericFont }}>
                  {formatMonths(goal.monthsBefore)} → {formatMonths(goal.monthsAfter)}
                </Typography>
              </Stack>
            ))}
          </Stack>
        </>
      )}
    </Stack>
  );
}

function planBounds(profile: CustomerProfile, goalId: string) {
  const goal = profile.goals.find((item) => item.id === goalId) ?? profile.goals[0];
  const remaining = Math.max(goal.target - goal.current, 0);
  const earliest = Math.max(Math.ceil(remaining / profile.monthlySavings), 1);
  const current = Math.max(Math.ceil(remaining / goal.monthlyContribution), earliest);
  return { earliest, current };
}

function GoalOptimizerTab({ profile }: { profile: CustomerProfile }) {
  const firstGoal = profile.goals[0];
  const initialBounds = planBounds(profile, firstGoal.id);
  const initialTarget = Math.max(
    initialBounds.earliest,
    Math.round((initialBounds.earliest + initialBounds.current) / 2),
  );
  const [goalId, setGoalId] = useState(firstGoal.id);
  const [targetMonths, setTargetMonths] = useState(initialTarget);
  const [result, setResult] = useState<GoalAllocationResult>(() =>
    calculateGoalAllocation(profile, firstGoal.id, initialTarget),
  );
  const [loading, setLoading] = useState(false);
  const bounds = planBounds(profile, goalId);

  function requestPlan(nextGoalId: string, months: number) {
    setLoading(true);
    optimizeGoalPlan(profile, nextGoalId, months)
      .then(setResult)
      .catch(() => setResult(calculateGoalAllocation(profile, nextGoalId, months)))
      .finally(() => setLoading(false));
  }

  function selectGoal(nextGoalId: string) {
    const nextBounds = planBounds(profile, nextGoalId);
    const nextTarget = Math.max(
      nextBounds.earliest,
      Math.round((nextBounds.earliest + nextBounds.current) / 2),
    );
    setGoalId(nextGoalId);
    setTargetMonths(nextTarget);
    requestPlan(nextGoalId, nextTarget);
  }

  function selectMonths(months: number) {
    setTargetMonths(months);
    requestPlan(goalId, months);
  }

  return (
    <Stack spacing={2}>
      <GoalSelect
        goals={profile.goals}
        value={goalId}
        onChange={selectGoal}
        label="Priority goal"
      />
      <Box>
        <Stack direction="row" justifyContent="space-between">
          <Typography variant="body2">Desired completion</Typography>
          <Typography variant="body2" sx={{ fontFamily: numericFont }}>
            {targetMonths} months
          </Typography>
        </Stack>
        <Slider
          value={targetMonths}
          min={bounds.earliest}
          max={Math.max(bounds.current, bounds.earliest + 1)}
          step={1}
          marks={[{ value: bounds.earliest }, { value: bounds.current }]}
          onChange={(_, value) => setTargetMonths(value as number)}
          onChangeCommitted={(_, value) => selectMonths(value as number)}
          aria-label="Desired goal completion months"
        />
        <Stack direction="row" justifyContent="space-between" sx={{ mt: -1 }}>
          <Typography variant="caption" sx={{ color: colors.inkSoft }}>Fastest</Typography>
          <Typography variant="caption" sx={{ color: colors.inkSoft }}>Current</Typography>
        </Stack>
      </Box>
      {loading ? <Skeleton height={170} /> : (
        <>
          <Alert severity={result.feasible ? 'success' : 'warning'}>{result.summary}</Alert>
          <Stack spacing={1}>
            {result.allocations.map((allocation) => (
              <Box
                key={allocation.goalId}
                sx={{ border: `1px solid ${colors.line}`, borderRadius: 2, p: 1.25 }}
              >
                <Stack direction="row" justifyContent="space-between">
                  <Typography variant="body2" fontWeight={600}>{allocation.goalName}</Typography>
                  <Typography variant="body2" sx={{ fontFamily: numericFont }}>
                    {formatCurrency(allocation.monthlyContributionBefore)} → {formatCurrency(allocation.monthlyContributionAfter)}/mo
                  </Typography>
                </Stack>
                <Typography variant="caption" sx={{ color: colors.inkSoft }}>
                  Timeline {formatMonths(allocation.monthsBefore)} → {formatMonths(allocation.monthsAfter)}
                </Typography>
              </Box>
            ))}
          </Stack>
        </>
      )}
    </Stack>
  );
}

export function DecisionLab({ profile, onAsk }: DecisionLabProps) {
  const [tab, setTab] = useState(0);
  return (
    <Card sx={{ p: { xs: 2, sm: 2.5 } }}>
      <Stack spacing={2}>
        <Stack spacing={0.5}>
          <Typography variant="h6" sx={{ color: colors.futureTeal }}>Decision Lab</Typography>
          <Typography variant="body2" sx={{ color: colors.inkSoft }}>
            Find a safe limit, stress-test the plan, or rebalance goal contributions.
          </Typography>
        </Stack>
        <Tabs
          value={tab}
          onChange={(_, value) => setTab(value)}
          variant="fullWidth"
          sx={{
            '& .MuiTab-root': {
              minWidth: 0,
              px: { xs: 0.5, sm: 1.5 },
              fontSize: { xs: '0.72rem', sm: '0.78rem' },
            },
          }}
          aria-label="Decision Lab tools"
        >
          <Tab label="Safe to Spend" />
          <Tab label="Stress Test" />
          <Tab label="Goal Optimizer" />
        </Tabs>
        {tab === 0 && <AffordabilityTab profile={profile} onAsk={onAsk} />}
        {tab === 1 && <StressTestTab profile={profile} />}
        {tab === 2 && <GoalOptimizerTab profile={profile} />}
      </Stack>
    </Card>
  );
}
