import { Box, Stack, Typography } from '@mui/material';
import { colors, numericFont } from '../../theme/theme';
import type { SimulationResult } from '../../lib/financialTools';

function monthLabel(months: number): string {
  if (!Number.isFinite(months)) return 'Not achievable';
  const date = new Date();
  date.setMonth(date.getMonth() + months);
  return new Intl.DateTimeFormat('en-NZ', {
    month: 'short',
    year: 'numeric',
  }).format(date);
}

export function FutureTimeline({ result }: { result: SimulationResult }) {
  const finiteMonths = result.goals.flatMap((goal) =>
    [goal.monthsBefore, goal.monthsAfter].filter(Number.isFinite),
  );
  const maximum = Math.max(12, ...finiteMonths) + 2;

  return (
    <Stack spacing={1.5}>
      <Stack direction="row" justifyContent="space-between" alignItems="center">
        <Typography variant="h6" sx={{ color: colors.inkSoft }}>Future timeline</Typography>
        <Stack direction="row" spacing={1.5}>
          <Stack direction="row" spacing={0.5} alignItems="center">
            <Box sx={{ width: 8, height: 8, borderRadius: '50%', border: `2px solid ${colors.inkSoft}` }} />
            <Typography variant="caption">Before</Typography>
          </Stack>
          <Stack direction="row" spacing={0.5} alignItems="center">
            <Box sx={{ width: 8, height: 8, borderRadius: '50%', bgcolor: colors.horizonGold }} />
            <Typography variant="caption">After</Typography>
          </Stack>
        </Stack>
      </Stack>

      {result.goals.map((goal) => {
        const beforePosition = Number.isFinite(goal.monthsBefore)
          ? Math.min(goal.monthsBefore / maximum * 100, 100)
          : 100;
        const afterPosition = Number.isFinite(goal.monthsAfter)
          ? Math.min(goal.monthsAfter / maximum * 100, 100)
          : 100;
        return (
          <Stack key={goal.goalId} spacing={0.75}>
            <Stack direction="row" justifyContent="space-between">
              <Typography variant="body2" fontWeight={600}>{goal.goalName}</Typography>
              <Typography variant="caption" sx={{ fontFamily: numericFont, color: colors.inkSoft }}>
                {monthLabel(goal.monthsBefore)} → {monthLabel(goal.monthsAfter)}
              </Typography>
            </Stack>
            <Box sx={{ position: 'relative', height: 22 }}>
              <Box
                sx={{
                  position: 'absolute',
                  top: 10,
                  left: 0,
                  right: 0,
                  height: 2,
                  bgcolor: colors.line,
                }}
              />
              <Box
                sx={{
                  position: 'absolute',
                  left: `${beforePosition}%`,
                  top: 4,
                  width: 12,
                  height: 12,
                  borderRadius: '50%',
                  border: `2px solid ${colors.inkSoft}`,
                  bgcolor: colors.paper,
                  transform: 'translateX(-50%)',
                }}
              />
              <Box
                sx={{
                  position: 'absolute',
                  left: `${afterPosition}%`,
                  top: 7,
                  width: 9,
                  height: 9,
                  borderRadius: '50%',
                  bgcolor: colors.horizonGold,
                  transform: 'translateX(-50%)',
                }}
              />
            </Box>
          </Stack>
        );
      })}
    </Stack>
  );
}
