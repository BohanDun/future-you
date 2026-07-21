import {
  Alert,
  Button,
  Card,
  CircularProgress,
  Divider,
  Stack,
  Typography,
} from '@mui/material';
import type { ChangePreview } from '../../lib/api';
import { colors } from '../../theme/theme';

interface Props {
  changes: ChangePreview[];
  applying: boolean;
  error: string | null;
  onApply: () => void;
  onCancel: () => void;
}

export function ActionProposal({ changes, applying, error, onApply, onCancel }: Props) {
  return (
    <Card sx={{ p: 2.5, borderColor: colors.horizonGold }}>
      <Stack spacing={2}>
        <Stack spacing={0.5}>
          <Typography variant="h6" sx={{ color: colors.horizonGold }}>Review changes</Typography>
          <Typography variant="body2" color="text.secondary">
            Nothing has been saved yet.
          </Typography>
        </Stack>
        {error && <Alert severity="error">{error}</Alert>}
        <Stack divider={<Divider flexItem />} spacing={1.5}>
          {changes.map((change, index) => (
            <Stack key={`${change.label}-${index}`} spacing={0.25}>
              <Typography variant="subtitle2">{change.label}</Typography>
              <Typography variant="body2" color="text.secondary">
                {change.before ? `${change.before} → ${change.after}` : change.after}
              </Typography>
            </Stack>
          ))}
        </Stack>
        <Stack direction="row" spacing={1.5} justifyContent="flex-end">
          <Button color="inherit" onClick={onCancel} disabled={applying}>Cancel</Button>
          <Button variant="contained" onClick={onApply} disabled={applying}>
            {applying ? <CircularProgress size={20} /> : 'Apply changes'}
          </Button>
        </Stack>
      </Stack>
    </Card>
  );
}
