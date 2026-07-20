import { Box, Card, Divider, Grid, Stack, Typography } from '@mui/material';
import { colors, numericFont } from '../../theme/theme';
import { formatCurrency, formatMonths } from '../../lib/format';
import type { SimulationResult } from '../../lib/financialTools';
import type { CustomerProfile } from '../../data/mockCustomer';
import { RiskBadge } from './RiskBadge';
import { Horizon } from './Horizon';
import { FutureTimeline } from './FutureTimeline';
import { RecoveryPlan } from './RecoveryPlan';

function Column({
  title,
  result,
  variant,
}: {
  title: string;
  result: SimulationResult;
  variant: 'before' | 'after';
}) {
  const balance = variant === 'before' ? result.balanceBefore : result.balanceAfter;
  const cashFlow = variant === 'before' ? result.monthlySavingsBefore : result.monthlySavingsAfter;
  const risk = variant === 'before' ? result.riskBefore : result.riskAfter;

  return (
    <Stack spacing={1.5} sx={{ flex: 1 }}>
      <Typography variant="h6" sx={{ color: variant === 'after' ? colors.horizonGold : colors.inkSoft }}>
        {title}
      </Typography>

      <Box>
        <Typography variant="caption" sx={{ color: colors.inkSoft }}>
          Balance
        </Typography>
        <Typography sx={{ fontFamily: numericFont, fontSize: '1.4rem', fontWeight: 500 }}>
          {formatCurrency(balance)}
        </Typography>
      </Box>

      <Box>
        <Typography variant="caption" sx={{ color: colors.inkSoft }}>
          Monthly cash flow
        </Typography>
        <Typography sx={{ fontFamily: numericFont, fontSize: '1.05rem', fontWeight: 500 }}>
          {formatCurrency(cashFlow)}
        </Typography>
      </Box>

      <Stack spacing={0.75}>
        {result.goals.map((g) => (
          <Stack direction="row" justifyContent="space-between" key={g.goalId}>
            <Typography variant="body2" sx={{ color: colors.inkSoft }}>
              {g.goalName}
            </Typography>
            <Typography sx={{ fontFamily: numericFont, fontSize: '0.85rem' }}>
              {formatMonths(variant === 'before' ? g.monthsBefore : g.monthsAfter)}
            </Typography>
          </Stack>
        ))}
      </Stack>

      <RiskBadge level={risk} />
    </Stack>
  );
}

export function ComparisonPanel({
  result,
  profile,
}: {
  result: SimulationResult;
  profile: CustomerProfile;
}) {
  const riskBackground = result.riskAfter === 'High'
    ? colors.riskHighSoft
    : result.riskAfter === 'Medium'
      ? colors.riskMediumSoft
      : colors.riskLowSoft;

  return (
    <Card sx={{ p: { xs: 2, sm: 3 } }}>
      <Stack spacing={2.5}>
        <Typography variant="h6" sx={{ color: colors.inkSoft }}>
          Before &amp; after — {result.scenario.description}
        </Typography>

        <Grid container spacing={{ xs: 2, sm: 0 }}>
          <Grid item xs={12} sm={5.5}>
            <Column title="Before" result={result} variant="before" />
          </Grid>
          <Grid item xs={12} sm={1} display="flex" justifyContent="center">
            <Divider orientation="vertical" flexItem sx={{ display: { xs: 'none', sm: 'block' } }} />
          </Grid>
          <Grid item xs={12} sm={5.5}>
            <Column title="After" result={result} variant="after" />
          </Grid>
        </Grid>

        <Horizon riskBefore={result.riskBefore} riskAfter={result.riskAfter} />

        <Divider />
        <FutureTimeline result={result} />

        <Box sx={{ bgcolor: riskBackground, borderRadius: 2, p: 2 }}>
          <Typography variant="h6" sx={{ color: colors.inkSoft, mb: 1 }}>
            Why this risk level
          </Typography>
          <Stack spacing={0.5}>
            {result.riskReasons.map((reason) => (
              <Typography key={reason} variant="body2">
                • {reason}
              </Typography>
            ))}
          </Stack>
        </Box>

        <RecoveryPlan profile={profile} result={result} />
      </Stack>
    </Card>
  );
}
