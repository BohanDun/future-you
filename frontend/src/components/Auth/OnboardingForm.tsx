import { FormEvent, useMemo, useState } from 'react';
import {
  Alert,
  Button,
  Card,
  Container,
  Grid,
  MenuItem,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import { saveCurrentUserProfile, type UserProfileInput } from '../../lib/api';
import type { CustomerProfile } from '../../data/mockCustomer';

interface Props {
  onComplete: (profile: CustomerProfile) => void;
  onLogout: () => Promise<void>;
}

const numberValue = (value: string) => Number.parseFloat(value) || 0;

export function OnboardingForm({ onComplete, onLogout }: Props) {
  const [name, setName] = useState('');
  const [currency, setCurrency] = useState('NZD');
  const [balance, setBalance] = useState('');
  const [income, setIncome] = useState('');
  const [expenses, setExpenses] = useState('');
  const [goalName, setGoalName] = useState('Emergency Fund');
  const [goalTarget, setGoalTarget] = useState('5000');
  const [goalCurrent, setGoalCurrent] = useState('0');
  const [goalContribution, setGoalContribution] = useState('250');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const monthlySavings = useMemo(
    () => numberValue(income) - numberValue(expenses),
    [income, expenses],
  );

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    const goalId = goalName.trim().toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_|_$/g, '') || 'primary_goal';
    const payload: UserProfileInput = {
      name: name.trim(),
      currency,
      currentBalance: numberValue(balance),
      monthlyIncome: numberValue(income),
      monthlyExpenses: numberValue(expenses),
      goals: [{
        goalId,
        name: goalName.trim(),
        target: numberValue(goalTarget),
        current: numberValue(goalCurrent),
        monthlyContribution: numberValue(goalContribution),
      }],
    };
    try {
      onComplete(await saveCurrentUserProfile(payload));
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : 'Could not save your profile.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <Container maxWidth="md" sx={{ py: { xs: 4, sm: 7 } }}>
      <Stack spacing={3}>
        <Stack spacing={1}>
          <Typography variant="h3">Tell us where you are today</Typography>
          <Typography color="text.secondary">
            We use this snapshot for deterministic simulations. You can update it later.
          </Typography>
        </Stack>
        <Card component="form" onSubmit={submit} sx={{ p: { xs: 3, sm: 4 } }}>
          <Stack spacing={3}>
            {error && <Alert severity="error">{error}</Alert>}
            <Typography variant="h6">Your financial snapshot</Typography>
            <Grid container spacing={2}>
              <Grid item xs={12} sm={8}>
                <TextField fullWidth required label="Preferred name" value={name} onChange={(event) => setName(event.target.value)} />
              </Grid>
              <Grid item xs={12} sm={4}>
                <TextField fullWidth select label="Currency" value={currency} onChange={(event) => setCurrency(event.target.value)}>
                  {['NZD', 'AUD', 'USD'].map((value) => <MenuItem key={value} value={value}>{value}</MenuItem>)}
                </TextField>
              </Grid>
              <Grid item xs={12} sm={4}>
                <TextField fullWidth required type="number" label="Available balance" inputProps={{ min: 0, step: 0.01 }} value={balance} onChange={(event) => setBalance(event.target.value)} />
              </Grid>
              <Grid item xs={12} sm={4}>
                <TextField fullWidth required type="number" label="Monthly income" inputProps={{ min: 0, step: 0.01 }} value={income} onChange={(event) => setIncome(event.target.value)} />
              </Grid>
              <Grid item xs={12} sm={4}>
                <TextField fullWidth required type="number" label="Monthly expenses" inputProps={{ min: 0, step: 0.01 }} value={expenses} onChange={(event) => setExpenses(event.target.value)} helperText={`Monthly cash flow: ${currency} ${monthlySavings.toFixed(2)}`} />
              </Grid>
            </Grid>
            <Typography variant="h6">Your first goal</Typography>
            <Grid container spacing={2}>
              <Grid item xs={12} sm={6}>
                <TextField fullWidth required label="Goal name" value={goalName} onChange={(event) => setGoalName(event.target.value)} />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField fullWidth required type="number" label="Target amount" inputProps={{ min: 0.01, step: 0.01 }} value={goalTarget} onChange={(event) => setGoalTarget(event.target.value)} />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField fullWidth required type="number" label="Already saved" inputProps={{ min: 0, step: 0.01 }} value={goalCurrent} onChange={(event) => setGoalCurrent(event.target.value)} />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField fullWidth required type="number" label="Monthly contribution" inputProps={{ min: 0, step: 0.01 }} value={goalContribution} onChange={(event) => setGoalContribution(event.target.value)} />
              </Grid>
            </Grid>
            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} justifyContent="space-between">
              <Button type="button" color="inherit" onClick={() => void onLogout()}>Sign out</Button>
              <Button type="submit" variant="contained" size="large" disabled={busy || !name.trim()}>
                {busy ? 'Saving…' : 'Create my dashboard'}
              </Button>
            </Stack>
          </Stack>
        </Card>
      </Stack>
    </Container>
  );
}
