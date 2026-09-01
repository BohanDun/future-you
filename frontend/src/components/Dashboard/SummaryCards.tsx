import { Card, Grid, Stack, Typography } from '@mui/material';
import { colors, numericFont } from '../../theme/theme';
import { formatCurrency } from '../../lib/format';
import type { CustomerProfile } from '../../data/mockCustomer';

function StatCard({
  label,
  value,
  accent,
}: {
  label: string;
  value: string;
  accent?: string;
}) {
  return (
    <Card sx={{ p: 2.5, height: '100%' }}>
      <Stack spacing={0.75}>
        <Typography variant="h6" sx={{ color: colors.inkSoft }}>
          {label}
        </Typography>
        <Typography
          sx={{
            fontFamily: numericFont,
            fontSize: { xs: '1.5rem', sm: '1.75rem' },
            fontWeight: 500,
            color: accent ?? colors.ink,
          }}
        >
          {value}
        </Typography>
      </Stack>
    </Card>
  );
}

export function SummaryCards({ profile }: { profile: CustomerProfile }) {
  return (
    <Grid container spacing={2}>
      <Grid item xs={12} sm={6} md={3}>
        <StatCard label="Current Balance" value={formatCurrency(profile.balance)} accent={colors.ink} />
      </Grid>
      <Grid item xs={12} sm={6} md={3}>
        <StatCard label="Monthly Income" value={formatCurrency(profile.monthlyIncome)} />
      </Grid>
      <Grid item xs={12} sm={6} md={3}>
        <StatCard label="Monthly Expenses" value={formatCurrency(profile.monthlyExpenses)} />
      </Grid>
      <Grid item xs={12} sm={6} md={3}>
        <StatCard
          label="Monthly Cash Flow"
          value={formatCurrency(profile.monthlySavings)}
          accent={colors.futureTeal}
        />
      </Grid>
    </Grid>
  );
}
