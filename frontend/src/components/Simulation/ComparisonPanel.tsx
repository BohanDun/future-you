import { Box, Card, Divider, Grid, Stack, Typography } from '@mui/material';
import { colors, numericFont } from '../../theme/theme';
import { formatCurrency, formatMonths } from '../../lib/format';
import type { SimulationResult } from '../../lib/financialTools';
import { RiskBadge } from './RiskBadge';
import { Horizon } from './Horizon';

function Column({
  title,
  result,
  variant,
}: {
  title: string;
  result: SimulationResult;
  variant: 'today' | 'event' | 'after';
}) {
  const balance = variant === 'today'
    ? result.balanceBefore
    : variant === 'event'
      ? (result.balanceAtEventBefore ?? result.balanceBefore)
      : result.balanceAfter;
  const cashFlow = variant === 'after' ? result.monthlySavingsAfter : result.monthlySavingsBefore;
  const risk = variant === 'today'
    ? result.riskBefore
    : variant === 'event'
      ? (result.eventRisk ?? result.riskAfter)
      : result.riskAfter;
  const duplicateNames = new Set(
    result.goals
      .filter((goal, index, goals) => goals.findIndex((item) => item.goalName === goal.goalName) !== index)
      .map((goal) => goal.goalName),
  );

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
          Available monthly cash
        </Typography>
        <Typography sx={{ fontFamily: numericFont, fontSize: '1.05rem', fontWeight: 500 }}>
          {formatCurrency(cashFlow)}
        </Typography>
      </Box>

      <Stack spacing={0.75}>
        {result.goals.map((g, index) => (
          <Stack direction="row" justifyContent="space-between" key={g.goalId}>
            <Typography variant="body2" sx={{ color: colors.inkSoft }}>
              {duplicateNames.has(g.goalName)
                ? `${g.goalName} ${result.goals.slice(0, index + 1).filter((item) => item.goalName === g.goalName).length}`
                : g.goalName}
            </Typography>
            <Typography sx={{ fontFamily: numericFont, fontSize: '0.85rem' }}>
              {variant === 'event' && g.currentAtEvent !== undefined
                ? formatCurrency(g.currentAtEvent)
                : variant === 'after'
                    && (result.scenario.horizonMonths ?? 0) > 0
                    && g.currentAfterEvent !== undefined
                  ? formatCurrency(g.currentAfterEvent)
                  : formatMonths(variant === 'after' ? g.monthsAfter : g.monthsBefore)}
            </Typography>
          </Stack>
        ))}
      </Stack>

      <RiskBadge level={risk} />
    </Stack>
  );
}

export function ComparisonPanel({ result }: { result: SimulationResult }) {
  const futureEvent = (result.scenario.horizonMonths ?? 0) > 0;
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
          <Grid item xs={12} sm={futureEvent ? 3.5 : 5.5}>
            <Column title="Today" result={result} variant="today" />
          </Grid>
          <Grid item xs={12} sm={futureEvent ? 0.5 : 1} display="flex" justifyContent="center">
            <Divider orientation="vertical" flexItem sx={{ display: { xs: 'none', sm: 'block' } }} />
          </Grid>
          {futureEvent && (
            <>
              <Grid item xs={12} sm={3.5}>
                <Column
                  title={`Month ${result.scenario.horizonMonths} — before`}
                  result={result}
                  variant="event"
                />
              </Grid>
              <Grid item xs={12} sm={0.5} display="flex" justifyContent="center">
                <Divider orientation="vertical" flexItem sx={{ display: { xs: 'none', sm: 'block' } }} />
              </Grid>
            </>
          )}
          <Grid item xs={12} sm={futureEvent ? 4 : 5.5}>
            <Column title={futureEvent ? 'After event' : 'After'} result={result} variant="after" />
          </Grid>
        </Grid>

        <Horizon
          riskBefore={result.riskBefore}
          riskAfter={result.riskAfter}
          endLabel={futureEvent ? `MONTH ${result.scenario.horizonMonths}` : 'FUTURE YOU'}
        />

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

        <Box sx={{ bgcolor: colors.horizonGoldSoft, borderRadius: 2, p: 2 }}>
          <Typography variant="h6" sx={{ color: colors.inkSoft, mb: 0.75 }}>
            Suggested adjustment
          </Typography>
          <Typography variant="body2">{result.recommendation}</Typography>
        </Box>
      </Stack>
    </Card>
  );
}
