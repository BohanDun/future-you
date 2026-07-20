import { Box, Stack, Typography } from '@mui/material';
import { colors } from '../../theme/theme';
import type { RiskLevel } from '../../lib/financialTools';

const riskColor: Record<RiskLevel, string> = {
  Low: colors.riskLow,
  Medium: colors.riskMedium,
  High: colors.riskHigh,
};

// The horizon: a line from "Now" to "Future You". The dot's vertical position
// encodes risk direction — it dips when risk worsens, lifts when it improves.
export function Horizon({ riskBefore, riskAfter }: { riskBefore: RiskLevel; riskAfter: RiskLevel }) {
  const order: Record<RiskLevel, number> = { Low: 0, Medium: 1, High: 2 };
  const worsened = order[riskAfter] > order[riskBefore];
  const improved = order[riskAfter] < order[riskBefore];
  const dipY = worsened ? 46 : improved ? 10 : 28;

  return (
    <Stack alignItems="center" spacing={0.5} sx={{ width: '100%' }}>
      <Box sx={{ width: '100%', maxWidth: 420 }}>
        <svg viewBox="0 0 420 60" width="100%" height="60" preserveAspectRatio="none">
          <defs>
            <linearGradient id="horizonLine" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stopColor={colors.line} />
              <stop offset="100%" stopColor={riskColor[riskAfter]} />
            </linearGradient>
          </defs>
          <path
            d={`M 8 28 Q 210 ${dipY} 412 28`}
            fill="none"
            stroke="url(#horizonLine)"
            strokeWidth={2}
            strokeLinecap="round"
          />
          <circle cx="8" cy="28" r="5" fill={riskColor[riskBefore]} />
          <circle cx="412" cy="28" r="6" fill={riskColor[riskAfter]} />
        </svg>
      </Box>
      <Stack direction="row" justifyContent="space-between" sx={{ width: '100%', maxWidth: 420, px: 0.25 }}>
        <Typography variant="caption" sx={{ color: colors.inkSoft, fontWeight: 600 }}>
          NOW
        </Typography>
        <Typography variant="caption" sx={{ color: colors.inkSoft, fontWeight: 600 }}>
          FUTURE YOU
        </Typography>
      </Stack>
    </Stack>
  );
}
