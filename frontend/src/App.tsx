import { useEffect, useState } from 'react';
import { Alert, Box, Button, CircularProgress, Container, Grid, Stack } from '@mui/material';
import { Header } from './components/Layout/Header';
import { DashboardSection } from './components/Dashboard/DashboardSection';
import { AgentSection } from './components/Chat/AgentSection';
import { mockCustomer } from './data/mockCustomer';
import type { CustomerProfile } from './data/mockCustomer';
import {
  addCurrentUserGoal,
  ApiError,
  deleteCurrentUserGoal,
  fetchCustomerProfile,
  ProfileNotFoundError,
  saveSpendingCategories,
} from './lib/api';
import { AuthScreen } from './components/Auth/AuthScreen';
import { OnboardingForm } from './components/Auth/OnboardingForm';
import { useAuth } from './context/useAuth';

export default function App() {
  const auth = useAuth();
  const [profile, setProfile] = useState<CustomerProfile | null>(null);
  const [profileError, setProfileError] = useState<string | null>(null);
  const [profileLoading, setProfileLoading] = useState(true);
  const [profileOwner, setProfileOwner] = useState<string | null>(null);
  const [needsOnboarding, setNeedsOnboarding] = useState(false);
  const [profileRequest, setProfileRequest] = useState(0);
  const currentUserId = auth.user?.userId ?? null;

  useEffect(() => {
    if (auth.enabled && !auth.user) return;
    let active = true;
    fetchCustomerProfile()
      .then((customer) => {
        if (active) {
          setProfile(customer);
          setProfileError(null);
          setNeedsOnboarding(false);
        }
      })
      .catch((error) => {
        if (active) {
          if (auth.enabled && error instanceof ProfileNotFoundError) {
            setProfile(null);
            setProfileError(null);
            setNeedsOnboarding(true);
          } else if (!auth.enabled) {
            setProfile(mockCustomer);
            setProfileError('Live customer data is unavailable, so the dashboard is showing demo data.');
          } else {
            const reason = error instanceof ApiError
              ? `Backend returned ${error.status}: ${error.message}`
              : error instanceof Error
                ? error.message
                : 'Unknown error';
            setProfileError(`Your profile could not be loaded. ${reason}`);
          }
        }
      })
      .finally(() => {
        if (active) {
          setProfileOwner(currentUserId);
          setProfileLoading(false);
        }
      });
    return () => {
      active = false;
    };
  }, [auth.enabled, auth.user, currentUserId, profileRequest]);

  if (auth.enabled && auth.loading) {
    return <Box sx={{ minHeight: '100vh', display: 'grid', placeItems: 'center' }}><CircularProgress /></Box>;
  }

  if (auth.enabled && !auth.user) return <AuthScreen />;

  if (auth.enabled && (profileLoading || profileOwner !== currentUserId)) {
    return <Box sx={{ minHeight: '100vh', display: 'grid', placeItems: 'center' }}><CircularProgress /></Box>;
  }

  if (auth.enabled && needsOnboarding) {
    return (
      <OnboardingForm
        onComplete={(customer) => {
          setProfile(customer);
          setNeedsOnboarding(false);
        }}
        onLogout={auth.logout}
      />
    );
  }

  if (auth.enabled && profileError) {
    return (
      <Box sx={{ minHeight: '100vh' }}>
        <Header onLogout={auth.logout} />
        <Container maxWidth="sm" sx={{ py: 8 }}>
          <Stack spacing={2}>
            <Alert severity="error">{profileError}</Alert>
            <Stack direction="row" spacing={2}>
              <Button
                variant="contained"
                onClick={() => {
                  setProfileLoading(true);
                  setProfileError(null);
                  setProfileRequest((request) => request + 1);
                }}
              >
                Try again
              </Button>
              <Button variant="outlined" onClick={auth.logout}>Sign out</Button>
            </Stack>
          </Stack>
        </Container>
      </Box>
    );
  }

  return (
    <Box sx={{ minHeight: '100vh' }}>
      <Header userName={profile?.name} onLogout={auth.enabled ? auth.logout : undefined} />
      <Container maxWidth="lg" sx={{ py: { xs: 3, sm: 5 } }}>
        {profileError && (
          <Alert severity="warning" sx={{ mb: 3 }}>
            {profileError}
          </Alert>
        )}
        <Grid container spacing={{ xs: 4, md: 5 }}>
          <Grid item xs={12} md={6}>
            {profile ? (
              <DashboardSection
                profile={profile}
                onAddGoal={auth.enabled ? async (goal) => {
                  setProfile(await addCurrentUserGoal(goal));
                } : undefined}
                onDeleteGoal={auth.enabled ? async (goalId) => {
                  setProfile(await deleteCurrentUserGoal(goalId));
                } : undefined}
                onSaveSpending={auth.enabled ? async (categories) => {
                  setProfile(await saveSpendingCategories(categories));
                } : undefined}
              />
            ) : <CircularProgress aria-label="Loading customer profile" />}
          </Grid>
          <Grid item xs={12} md={6}>
            <AgentSection onProfileUpdated={setProfile} />
          </Grid>
        </Grid>
      </Container>
    </Box>
  );
}
