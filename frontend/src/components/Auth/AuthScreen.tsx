import { FormEvent, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Card,
  Container,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import { colors } from '../../theme/theme';
import {
  authConfigurationError,
  confirmRegisteredUser,
  loginUser,
  registerUser,
} from '../../lib/auth';
import { useAuth } from '../../context/useAuth';

type Mode = 'login' | 'signup' | 'confirm';

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : 'Authentication failed. Please try again.';
}

export function AuthScreen() {
  const { refresh } = useAuth();
  const [mode, setMode] = useState<Mode>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [code, setCode] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(authConfigurationError);
  const [notice, setNotice] = useState<string | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (authConfigurationError) return;
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      if (mode === 'signup') {
        const result = await registerUser(email, password);
        if (result.nextStep.signUpStep === 'CONFIRM_SIGN_UP') {
          setMode('confirm');
          setNotice('Check your email for the verification code.');
        } else {
          setMode('login');
          setNotice('Account created. You can now sign in.');
        }
      } else if (mode === 'confirm') {
        await confirmRegisteredUser(email, code);
        setMode('login');
        setNotice('Email verified. Sign in to continue.');
      } else {
        const result = await loginUser(email, password);
        if (result.nextStep.signInStep === 'DONE') {
          await refresh();
        } else if (result.nextStep.signInStep === 'CONFIRM_SIGN_UP') {
          setMode('confirm');
          setNotice('Verify your email before signing in.');
        } else {
          setError(`Additional sign-in step required: ${result.nextStep.signInStep}`);
        }
      }
    } catch (authError) {
      setError(errorMessage(authError));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Box sx={{ minHeight: '100vh', display: 'grid', placeItems: 'center', py: 5 }}>
      <Container maxWidth="sm">
        <Stack spacing={3} alignItems="center">
          <Stack spacing={1} alignItems="center" textAlign="center">
            <Typography variant="h3">Future You</Typography>
            <Typography color="text.secondary">
              See how today's money choices shape tomorrow.
            </Typography>
          </Stack>
          <Card component="form" onSubmit={submit} sx={{ width: '100%', p: { xs: 3, sm: 4 } }}>
            <Stack spacing={2.5}>
              <Typography variant="h5">
                {mode === 'login' ? 'Sign in' : mode === 'signup' ? 'Create your account' : 'Verify your email'}
              </Typography>
              {error && <Alert severity="error">{error}</Alert>}
              {notice && <Alert severity="success">{notice}</Alert>}
              <TextField
                label="Email"
                type="email"
                required
                autoComplete="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                disabled={mode === 'confirm' || busy}
              />
              {mode === 'confirm' ? (
                <TextField
                  label="Verification code"
                  required
                  inputMode="numeric"
                  value={code}
                  onChange={(event) => setCode(event.target.value)}
                  disabled={busy}
                />
              ) : (
                <TextField
                  label="Password"
                  type="password"
                  required
                  autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  disabled={busy}
                  helperText={mode === 'signup' ? 'Use the password policy configured in Cognito.' : undefined}
                />
              )}
              <Button type="submit" variant="contained" size="large" disabled={busy || Boolean(authConfigurationError)}>
                {busy ? 'Please wait…' : mode === 'login' ? 'Sign in' : mode === 'signup' ? 'Create account' : 'Verify email'}
              </Button>
              <Button
                type="button"
                onClick={() => {
                  setMode(mode === 'login' ? 'signup' : 'login');
                  setError(null);
                  setNotice(null);
                }}
                sx={{ color: colors.futureTeal }}
              >
                {mode === 'login' ? 'New to Future You? Create an account' : 'Already have an account? Sign in'}
              </Button>
            </Stack>
          </Card>
        </Stack>
      </Container>
    </Box>
  );
}
