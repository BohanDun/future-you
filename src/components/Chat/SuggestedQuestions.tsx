import { Chip, Stack } from '@mui/material';
import { colors } from '../../theme/theme';

export function SuggestedQuestions({
  questions,
  onSelect,
  disabled,
}: {
  questions: string[];
  onSelect: (q: string) => void;
  disabled?: boolean;
}) {
  return (
    <Stack direction="row" flexWrap="wrap" gap={1}>
      {questions.map((q) => (
        <Chip
          key={q}
          label={q}
          variant="outlined"
          disabled={disabled}
          onClick={() => onSelect(q)}
          sx={{
            borderColor: colors.line,
            color: colors.inkSoft,
            bgcolor: colors.surface,
            '&:hover': { bgcolor: colors.horizonGoldSoft, borderColor: colors.horizonGold },
          }}
        />
      ))}
    </Stack>
  );
}
