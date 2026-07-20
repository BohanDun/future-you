import { Card, Stack, Typography } from '@mui/material';
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { colors, numericFont } from '../../theme/theme';
import { diningInsight, type CustomerProfile } from '../../data/mockCustomer';
import { formatCurrency } from '../../lib/format';

export function SpendingChart({ profile }: { profile: CustomerProfile }) {
  return (
    <Card sx={{ p: 2.5, height: '100%' }}>
      <Stack spacing={2} sx={{ height: '100%' }}>
        <Stack spacing={0.5}>
          <Typography variant="h6" sx={{ color: colors.inkSoft }}>
            Spending by category
          </Typography>
          <Typography variant="body2" sx={{ color: colors.inkSoft }}>
            {diningInsight()}
          </Typography>
        </Stack>

        <div style={{ width: '100%', height: 220 }}>
          <ResponsiveContainer>
            <BarChart data={profile.spendingCategories} margin={{ top: 4, right: 8, left: -16, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={colors.line} vertical={false} />
              <XAxis
                dataKey="category"
                tick={{ fill: colors.inkSoft, fontSize: 12 }}
                axisLine={{ stroke: colors.line }}
                tickLine={false}
              />
              <YAxis
                tick={{ fill: colors.inkSoft, fontSize: 12 }}
                axisLine={false}
                tickLine={false}
                width={56}
              />
              <Tooltip
                formatter={(value: number) => formatCurrency(value)}
                contentStyle={{
                  fontFamily: numericFont,
                  border: `1px solid ${colors.line}`,
                  borderRadius: 8,
                }}
              />
              <Bar dataKey="amount" fill={colors.horizonGold} radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </Stack>
    </Card>
  );
}
