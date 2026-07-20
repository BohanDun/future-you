import { Box, Stack, Typography, CircularProgress } from '@mui/material';
import { colors } from '../../theme/theme';

export interface Message {
  id: string;
  role: 'user' | 'agent';
  text: string;
  pending?: boolean;
}

export function ChatMessage({ message }: { message: Message }) {
  const isUser = message.role === 'user';
  return (
    <Stack direction="row" justifyContent={isUser ? 'flex-end' : 'flex-start'}>
      <Box
        sx={{
          maxWidth: '82%',
          px: 2,
          py: 1.25,
          borderRadius: isUser ? '14px 14px 4px 14px' : '14px 14px 14px 4px',
          bgcolor: isUser ? colors.ink : colors.futureTealSoft,
          color: isUser ? '#FFFFFF' : colors.ink,
        }}
      >
        {message.pending ? (
          <Stack direction="row" spacing={1.25} alignItems="center" sx={{ py: 0.25 }}>
            <CircularProgress size={14} thickness={5} sx={{ color: colors.futureTeal }} />
            <Typography variant="body2" sx={{ color: colors.inkSoft }}>
              Future You is thinking…
            </Typography>
          </Stack>
        ) : (
          <Typography variant="body2" sx={{ whiteSpace: 'pre-line', lineHeight: 1.55 }}>
            {message.text}
          </Typography>
        )}
      </Box>
    </Stack>
  );
}
