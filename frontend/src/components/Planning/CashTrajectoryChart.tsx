import { Box, Chip, Stack, Typography } from '@mui/material';
import type { CustomerProfile } from '../../data/mockCustomer';
import { buildCashTrajectory } from '../../lib/financialTools';
import { formatCurrency } from '../../lib/format';
import { colors, numericFont } from '../../theme/theme';

interface CashTrajectoryChartProps {
  profile: CustomerProfile;
  incomeLossMonths: number;
  unexpectedExpense: number;
}

export function CashTrajectoryChart({
  profile,
  incomeLossMonths,
  unexpectedExpense,
}: CashTrajectoryChartProps) {
  const points = buildCashTrajectory(profile, incomeLossMonths, unexpectedExpense);
  const values = points.map((point) => point.balance);
  const minimum = Math.min(0, ...values);
  const maximum = Math.max(0, ...values);
  const span = Math.max(maximum - minimum, 1);
  const x = (month: number) => month / 12 * 100;
  const y = (balance: number) => 3 + (maximum - balance) / span * 34;
  const linePoints = points.map((point) => `${x(point.month)},${y(point.balance)}`).join(' ');
  const zeroY = y(0);
  const shockEndX = x(incomeLossMonths);
  const recovery = points.find(
    (point) => point.month > incomeLossMonths && point.balance >= profile.balance,
  );
  const finalBalance = points[points.length - 1].balance;

  return (
    <Box sx={{ border: `1px solid ${colors.line}`, borderRadius: 2, p: 1.5 }}>
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }}>
        <Box>
          <Typography variant="body2" fontWeight={700}>12-month cash recovery</Typography>
          <Typography variant="caption" sx={{ color: colors.inkSoft }}>
            Shock first, then rebuild using current monthly savings.
          </Typography>
        </Box>
        <Chip
          size="small"
          label={recovery ? `Recovered month ${recovery.month}` : 'Beyond 12 months'}
          sx={{
            bgcolor: recovery ? colors.futureTealSoft : colors.riskHighSoft,
            color: recovery ? colors.futureTeal : colors.riskHigh,
          }}
        />
      </Stack>

      <Box sx={{ width: '100%', overflow: 'hidden' }}>
        <svg
          viewBox="0 0 100 40"
          width="100%"
          role="img"
          aria-label={`Projected cash position reaches ${formatCurrency(finalBalance)} after 12 months`}
          preserveAspectRatio="none"
          style={{ display: 'block', height: 150 }}
        >
          <defs>
            <linearGradient id="cash-recovery-fill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={colors.futureTeal} stopOpacity="0.22" />
              <stop offset="100%" stopColor={colors.futureTeal} stopOpacity="0.02" />
            </linearGradient>
          </defs>
          <line
            x1="0"
            x2="100"
            y1={zeroY}
            y2={zeroY}
            stroke={colors.riskHigh}
            strokeWidth="0.45"
            strokeDasharray="2 2"
          />
          {incomeLossMonths > 0 && (
            <line
              x1={shockEndX}
              x2={shockEndX}
              y1="2"
              y2="38"
              stroke={colors.horizonGold}
              strokeWidth="0.5"
              strokeDasharray="2 1.5"
            />
          )}
          <polygon
            points={`0,37 ${linePoints} 100,37`}
            fill="url(#cash-recovery-fill)"
          />
          <polyline
            points={linePoints}
            fill="none"
            stroke={colors.futureTeal}
            strokeWidth="1.3"
            strokeLinejoin="round"
            strokeLinecap="round"
            vectorEffect="non-scaling-stroke"
          />
          {points.map((point) => (
            <circle
              key={point.month}
              cx={x(point.month)}
              cy={y(point.balance)}
              r={point.month === 0 || point.month === incomeLossMonths || point.month === 12 ? 1.1 : 0.55}
              fill={point.balance < 0 ? colors.riskHigh : colors.futureTeal}
            />
          ))}
        </svg>
      </Box>

      <Stack direction="row" justifyContent="space-between" sx={{ mt: 0.5 }}>
        <Box>
          <Typography variant="caption" sx={{ color: colors.inkSoft }}>After expense</Typography>
          <Typography variant="body2" sx={{ fontFamily: numericFont }}>
            {formatCurrency(points[0].balance)}
          </Typography>
        </Box>
        {incomeLossMonths > 0 && (
          <Box sx={{ textAlign: 'center' }}>
            <Typography variant="caption" sx={{ color: colors.inkSoft }}>Shock ends</Typography>
            <Typography variant="body2" sx={{ fontFamily: numericFont }}>
              Month {incomeLossMonths}
            </Typography>
          </Box>
        )}
        <Box sx={{ textAlign: 'right' }}>
          <Typography variant="caption" sx={{ color: colors.inkSoft }}>Month 12</Typography>
          <Typography variant="body2" sx={{ fontFamily: numericFont }}>
            {formatCurrency(finalBalance)}
          </Typography>
        </Box>
      </Stack>
    </Box>
  );
}
