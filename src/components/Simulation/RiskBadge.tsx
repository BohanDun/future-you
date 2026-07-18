import { Chip } from '@mui/material';
import { colors } from '../../theme/theme';
import type { RiskLevel } from '../../lib/financialTools';

const styles: Record<RiskLevel, { fg: string; bg: string }> = {
  Low: { fg: colors.riskLow, bg: colors.riskLowSoft },
  Medium: { fg: colors.riskMedium, bg: colors.riskMediumSoft },
  High: { fg: colors.riskHigh, bg: colors.riskHighSoft },
};

export function RiskBadge({ level }: { level: RiskLevel }) {
  const s = styles[level];
  return (
    <Chip
      label={`${level} risk`}
      size="small"
      sx={{
        color: s.fg,
        bgcolor: s.bg,
        fontWeight: 700,
        fontSize: '0.72rem',
      }}
    />
  );
}
