import { Box, Container, Stack, Typography } from '@mui/material';
import { colors } from '../../theme/theme';

export function Header() {
  return (
    <Box
      component="header"
      sx={{
        borderBottom: `1px solid ${colors.line}`,
        bgcolor: colors.surface,
      }}
    >
      <Container maxWidth="lg">
        <Stack
          direction="row"
          alignItems="center"
          justifyContent="space-between"
          sx={{ py: 2.5 }}
        >
          <Stack direction="row" alignItems="baseline" spacing={1.25}>
            <Box
              sx={{
                width: 10,
                height: 10,
                borderRadius: '50%',
                background: `linear-gradient(135deg, ${colors.horizonGold}, ${colors.futureTeal})`,
              }}
            />
            <Typography variant="h5" component="span" sx={{ fontSize: '1.35rem' }}>
              Future You
            </Typography>
          </Stack>
          <Typography
            variant="body2"
            sx={{ color: colors.inkSoft, display: { xs: 'none', sm: 'block' } }}
          >
            Most banks tell you what happened. Future You shows you what will happen.
          </Typography>
        </Stack>
      </Container>
    </Box>
  );
}
