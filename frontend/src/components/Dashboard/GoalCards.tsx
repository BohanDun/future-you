import { Card, Grid, LinearProgress, Stack, Typography, Box } from '@mui/material';
import { colors, numericFont } from '../../theme/theme';
import { formatCurrency } from '../../lib/format';
import type { Goal } from '../../data/mockCustomer';

function monthsRemaining(goal: Goal): number {
  const remaining = goal.target - goal.current;
  if (remaining <= 0) return 0;
  return Math.ceil(remaining / goal.monthlyContribution);
}

function GoalCard({ goal }: { goal: Goal }) {
  const pct = Math.min(100, Math.round((goal.current / goal.target) * 100));
  const months = monthsRemaining(goal);

  return (
    <Card sx={{ p: 2.5, height: '100%' }}>
      <Stack spacing={1.5}>
        <Stack direction="row" justifyContent="space-between" alignItems="baseline">
          <Typography variant="subtitle1" sx={{ fontFamily: '"Fraunces", serif', fontWeight: 600 }}>
            {goal.name}
          </Typography>
          <Typography sx={{ fontFamily: numericFont, fontSize: '0.8rem', color: colors.inkSoft }}>
            {pct}%
          </Typography>
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
              {months === 0 ? 'Reached' : `${months} mo`}
            </Typography>
            <Typography variant="caption" sx={{ color: colors.inkSoft }}>
              at current pace
            </Typography>
          </Box>
        </Stack>
      </Stack>
    </Card>
  );
}

export function GoalCards({ goals }: { goals: Goal[] }) {
  return (
    <Grid container spacing={2}>
      {goals.map((g) => (
        <Grid item xs={12} sm={6} md={4} key={g.id}>
          <GoalCard goal={g} />
        </Grid>
      ))}
    </Grid>
  );
}
