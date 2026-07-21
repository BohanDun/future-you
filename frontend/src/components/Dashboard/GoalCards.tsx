import { FormEvent, useState } from 'react';
import AddIcon from '@mui/icons-material/Add';
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline';
import {
  Alert,
  Box,
  Button,
  Card,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Grid,
  IconButton,
  LinearProgress,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import { colors, numericFont } from '../../theme/theme';
import { formatCurrency } from '../../lib/format';
import type { Goal } from '../../data/mockCustomer';

function monthsRemaining(goal: Goal): number {
  const remaining = goal.target - goal.current;
  if (remaining <= 0) return 0;
  if (goal.monthlyContribution <= 0) return Infinity;
  return Math.ceil(remaining / goal.monthlyContribution);
}

function GoalCard({ goal, onDelete }: { goal: Goal; onDelete?: () => void }) {
  const pct = Math.min(100, Math.round((goal.current / goal.target) * 100));
  const months = monthsRemaining(goal);

  return (
    <Card sx={{ p: 2.5, height: '100%' }}>
      <Stack spacing={1.5}>
        <Stack direction="row" justifyContent="space-between" alignItems="center">
          <Typography variant="subtitle1" sx={{ fontFamily: '"Fraunces", serif', fontWeight: 600 }}>
            {goal.name}
          </Typography>
          <Stack direction="row" spacing={0.5} alignItems="center">
            <Typography sx={{ fontFamily: numericFont, fontSize: '0.8rem', color: colors.inkSoft }}>
              {pct}%
            </Typography>
            {onDelete && (
              <IconButton
                size="small"
                color="error"
                aria-label={`Delete ${goal.name} goal`}
                onClick={onDelete}
              >
                <DeleteOutlineIcon fontSize="small" />
              </IconButton>
            )}
          </Stack>
        </Stack>

        <LinearProgress
          variant="determinate"
          value={pct}
          sx={{
            height: 8,
            borderRadius: 999,
            bgcolor: colors.line,
            '& .MuiLinearProgress-bar': {
              borderRadius: 999,
              backgroundColor: colors.futureTeal,
            },
          }}
        />

        <Stack direction="row" justifyContent="space-between">
          <Box>
            <Typography sx={{ fontFamily: numericFont, fontSize: '0.95rem' }}>
              {formatCurrency(goal.current)}
            </Typography>
            <Typography variant="caption" sx={{ color: colors.inkSoft }}>
              of {formatCurrency(goal.target)}
            </Typography>
          </Box>
          <Box textAlign="right">
            <Typography sx={{ fontFamily: numericFont, fontSize: '0.95rem' }}>
              {months === 0 ? 'Reached' : months === Infinity ? 'Paused' : `${months} mo`}
            </Typography>
            <Typography variant="caption" sx={{ color: colors.inkSoft }}>
              at current pace
            </Typography>
          </Box>
        </Stack>

        <Box
          sx={{
            pt: 1.25,
            borderTop: `1px solid ${colors.line}`,
          }}
        >
          <Typography variant="caption" sx={{ color: colors.inkSoft }}>
            Monthly goal
          </Typography>
          <Typography sx={{ fontFamily: numericFont, fontSize: '0.95rem' }}>
            {formatCurrency(goal.monthlyContribution)} / month
          </Typography>
        </Box>
      </Stack>
    </Card>
  );
}

interface Props {
  goals: Goal[];
  onAddGoal?: (goal: Goal) => Promise<void>;
  onDeleteGoal?: (goalId: string) => Promise<void>;
}

const numberValue = (value: string) => Number.parseFloat(value);

export function GoalCards({ goals, onAddGoal, onDeleteGoal }: Props) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState('');
  const [target, setTarget] = useState('');
  const [current, setCurrent] = useState('0');
  const [contribution, setContribution] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [deleteGoal, setDeleteGoal] = useState<Goal | null>(null);
  const [deleteBusy, setDeleteBusy] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  function close() {
    if (busy) return;
    setOpen(false);
    setError(null);
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!onAddGoal) return;

    const targetAmount = numberValue(target);
    const currentAmount = numberValue(current);
    const monthlyContribution = numberValue(contribution);
    if (targetAmount <= 0 || currentAmount < 0 || monthlyContribution < 0) {
      setError('Enter a positive target and non-negative saved amount and monthly contribution.');
      return;
    }

    const baseId = name.trim().toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_|_$/g, '') || 'goal';
    const existingIds = new Set(goals.map((goal) => goal.id));
    let goalId = baseId;
    let suffix = 2;
    while (existingIds.has(goalId)) {
      goalId = `${baseId}_${suffix}`;
      suffix += 1;
    }

    setBusy(true);
    setError(null);
    try {
      await onAddGoal({
        id: goalId,
        name: name.trim(),
        target: targetAmount,
        current: currentAmount,
        monthlyContribution,
      });
      setOpen(false);
      setName('');
      setTarget('');
      setCurrent('0');
      setContribution('');
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : 'Could not add the goal.');
    } finally {
      setBusy(false);
    }
  }

  async function confirmDelete() {
    if (!deleteGoal || !onDeleteGoal || deleteBusy) return;
    setDeleteBusy(true);
    setDeleteError(null);
    try {
      await onDeleteGoal(deleteGoal.id);
      setDeleteGoal(null);
    } catch (deleteFailure) {
      setDeleteError(
        deleteFailure instanceof Error ? deleteFailure.message : 'Could not delete the goal.',
      );
    } finally {
      setDeleteBusy(false);
    }
  }

  return (
    <Stack spacing={1.5}>
      <Stack direction="row" alignItems="center" justifyContent="space-between">
        <Typography variant="h6">Goals</Typography>
        {onAddGoal && (
          <Button
            size="small"
            startIcon={<AddIcon />}
            onClick={() => setOpen(true)}
            disabled={goals.length >= 10}
          >
            Add goal
          </Button>
        )}
      </Stack>
      <Grid container spacing={2}>
        {goals.map((g) => (
          <Grid item xs={12} sm={6} md={4} key={g.id}>
            <GoalCard
              goal={g}
              onDelete={onDeleteGoal ? () => {
                setDeleteError(null);
                setDeleteGoal(g);
              } : undefined}
            />
          </Grid>
        ))}
      </Grid>
      {onAddGoal && goals.length >= 10 && (
        <Typography variant="caption" color="text.secondary">You can have up to 10 goals.</Typography>
      )}
      <Dialog open={open} onClose={close} fullWidth maxWidth="sm">
        <Box component="form" onSubmit={submit}>
          <DialogTitle>Add a financial goal</DialogTitle>
          <DialogContent>
            <Stack spacing={2} sx={{ pt: 1 }}>
              {error && <Alert severity="error">{error}</Alert>}
              <TextField required autoFocus label="Goal name" value={name} onChange={(event) => setName(event.target.value)} />
              <TextField required type="number" label="Target amount" inputProps={{ min: 0.01, step: 0.01 }} value={target} onChange={(event) => setTarget(event.target.value)} />
              <TextField required type="number" label="Already saved" inputProps={{ min: 0, step: 0.01 }} value={current} onChange={(event) => setCurrent(event.target.value)} />
              <TextField required type="number" label="Monthly contribution" inputProps={{ min: 0, step: 0.01 }} value={contribution} onChange={(event) => setContribution(event.target.value)} />
            </Stack>
          </DialogContent>
          <DialogActions sx={{ px: 3, pb: 3 }}>
            <Button onClick={close} color="inherit" disabled={busy}>Cancel</Button>
            <Button type="submit" variant="contained" disabled={busy || !name.trim()}>
              {busy ? 'Saving…' : 'Add goal'}
            </Button>
          </DialogActions>
        </Box>
      </Dialog>
      <Dialog
        open={Boolean(deleteGoal)}
        onClose={() => {
          if (!deleteBusy) setDeleteGoal(null);
        }}
        fullWidth
        maxWidth="xs"
      >
        <DialogTitle>Delete goal?</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ pt: 0.5 }}>
            {deleteError && <Alert severity="error">{deleteError}</Alert>}
            <Typography>
              {deleteGoal
                ? `This will permanently remove “${deleteGoal.name}” from your profile.`
                : ''}
            </Typography>
          </Stack>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 3 }}>
          <Button
            color="inherit"
            disabled={deleteBusy}
            onClick={() => setDeleteGoal(null)}
          >
            Cancel
          </Button>
          <Button
            color="error"
            variant="contained"
            disabled={deleteBusy}
            onClick={() => void confirmDelete()}
          >
            {deleteBusy ? 'Deleting…' : 'Delete goal'}
          </Button>
        </DialogActions>
      </Dialog>
    </Stack>
  );
}
