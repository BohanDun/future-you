import { lazy, Suspense } from 'react';
import { Skeleton, Stack, Typography } from '@mui/material';
import { colors } from '../../theme/theme';
import type { CustomerProfile } from '../../data/mockCustomer';
import { SummaryCards } from './SummaryCards';
import { GoalCards } from './GoalCards';

const SpendingChart = lazy(() =>
  import('./SpendingChart').then((module) => ({ default: module.SpendingChart })),
);

export function DashboardSection({ profile }: { profile: CustomerProfile }) {
  return (
    <Stack spacing={3}>
      <Stack spacing={0.5}>
        <Typography variant="h6" sx={{ color: colors.horizonGold }}>
          Today
        </Typography>
        <Typography variant="h4">Good to see you, {profile.name}.</Typography>
      </Stack>

      <SummaryCards profile={profile} />
      <GoalCards goals={profile.goals} />
      <Suspense fallback={<Skeleton variant="rounded" height={344} />}>
        <SpendingChart profile={profile} />
      </Suspense>
    </Stack>
  );
}
