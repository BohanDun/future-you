import { Box, Stack, Typography } from '@mui/material';
import { colors } from '../../theme/theme';
import type { CustomerProfile } from '../../data/mockCustomer';
import { buildRecoveryOptions, type SimulationResult } from '../../lib/financialTools';

export function RecoveryPlan({
  profile,
  result,
}: {
  profile: CustomerProfile;
  result: SimulationResult;
}) {
  const options = buildRecoveryOptions(profile, result);
  return (
    <Stack spacing={1.25}>
      <Stack spacing={0.25}>
        <Typography variant="h6" sx={{ color: colors.inkSoft }}>Make it work</Typography>
        <Typography variant="body2" sx={{ color: colors.inkSoft }}>
          Recommended first step: {result.recommendation}
        </Typography>
      </Stack>
      {options.map((option, index) => (
        <Box
          key={option.title}
          sx={{
            border: `1px solid ${colors.line}`,
            borderRadius: 2,
            p: 1.5,
            bgcolor: index === 0 ? colors.horizonGoldSoft : colors.paper,
          }}
        >
          <Stack direction="row" spacing={1.25} alignItems="flex-start">
            <Box
              sx={{
                minWidth: 24,
                height: 24,
                borderRadius: '50%',
                display: 'grid',
                placeItems: 'center',
                bgcolor: index === 0 ? colors.horizonGold : colors.line,
                color: colors.ink,
                fontSize: '0.75rem',
                fontWeight: 700,
              }}
            >
              {index + 1}
            </Box>
            <Stack spacing={0.25}>
              <Typography variant="body2" fontWeight={700}>{option.title}</Typography>
              <Typography variant="body2">{option.description}</Typography>
              <Typography variant="caption" sx={{ color: colors.inkSoft }}>{option.impact}</Typography>
            </Stack>
          </Stack>
        </Box>
      ))}
    </Stack>
  );
}
