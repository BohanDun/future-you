import { useEffect, useState } from 'react';
import { Box, Card, LinearProgress, Stack, Typography } from '@mui/material';
import type { CustomerProfile } from '../../data/mockCustomer';
import { fetchFinancialHealth } from '../../lib/api';
import {
  calculateFinancialHealth,
  type FinancialHealthScore,
} from '../../lib/financialTools';
import { colors, numericFont } from '../../theme/theme';

function scoreColor(score: number): string {
  if (score >= 80) return colors.futureTeal;
  if (score >= 65) return colors.horizonGold;
  if (score >= 45) return colors.riskMedium;
  return colors.riskHigh;
}

export function FinancialHealthCard({ profile }: { profile: CustomerProfile }) {
  const [health, setHealth] = useState<FinancialHealthScore>(() =>
    calculateFinancialHealth(profile),
  );

  useEffect(() => {
    let active = true;
    fetchFinancialHealth(profile)
      .then((result) => {
        if (active) setHealth(result);
      })
      .catch(() => {
        if (active) setHealth(calculateFinancialHealth(profile));
      });
    return () => {
      active = false;
    };
  }, [profile]);

  const accent = scoreColor(health.score);

  return (
    <Card sx={{ p: { xs: 2, sm: 2.5 } }}>
      <Stack spacing={2.25}>
        <Stack direction="row" justifyContent="space-between" alignItems="flex-start">
          <Box>
            <Typography variant="h6" sx={{ color: colors.futureTeal }}>
              Money Health
            </Typography>
            <Typography variant="body2" sx={{ color: colors.inkSoft, mt: 0.5 }}>
              A transparent score based on savings, reserves and goal progress.
            </Typography>
          </Box>
          <Box
            aria-label={`Money health score ${health.score} out of 100, ${health.status}`}
            sx={{
              flex: '0 0 auto',
              width: 86,
              height: 86,
              ml: 2,
              borderRadius: '50%',
              display: 'grid',
              placeItems: 'center',
              background: `conic-gradient(${accent} ${health.score}%, ${colors.line} 0)`,
              position: 'relative',
              '&::after': {
                content: '""',
                position: 'absolute',
                inset: 7,
                borderRadius: '50%',
                bgcolor: colors.surface,
              },
            }}
          >
            <Stack spacing={0} alignItems="center" sx={{ position: 'relative', zIndex: 1 }}>
              <Typography sx={{ fontFamily: numericFont, fontSize: '1.45rem', lineHeight: 1 }}>
                {health.score}
              </Typography>
              <Typography variant="caption" sx={{ color: accent, fontWeight: 700 }}>
                {health.status}
              </Typography>
            </Stack>
          </Box>
        </Stack>

        <Stack spacing={1.5}>
          {health.components.map((component) => (
            <Box key={component.key}>
              <Stack direction="row" justifyContent="space-between" alignItems="baseline">
                <Typography variant="body2" fontWeight={600}>{component.label}</Typography>
                <Typography variant="caption" sx={{ color: colors.inkSoft }}>
                  {component.summary}
                </Typography>
              </Stack>
              <LinearProgress
                variant="determinate"
                value={component.maxScore > 0 ? component.score / component.maxScore * 100 : 0}
                aria-label={`${component.label}: ${component.score} of ${component.maxScore} points`}
                sx={{
                  mt: 0.75,
                  height: 7,
                  borderRadius: 4,
                  bgcolor: colors.line,
                  '& .MuiLinearProgress-bar': { bgcolor: accent, borderRadius: 4 },
                }}
              />
            </Box>
          ))}
        </Stack>

        <Box sx={{ bgcolor: colors.futureTealSoft, borderRadius: 2, p: 1.5 }}>
          <Typography variant="caption" sx={{ color: colors.futureTeal, fontWeight: 700 }}>
            NEXT BEST ACTION
          </Typography>
          <Typography variant="body2" sx={{ mt: 0.25 }}>
            {health.nextBestAction}
          </Typography>
        </Box>
      </Stack>
    </Card>
  );
}
