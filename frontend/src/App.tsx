import { useEffect, useState } from 'react';
import { Alert, Box, CircularProgress, Container, Grid } from '@mui/material';
import { Header } from './components/Layout/Header';
import { DashboardSection } from './components/Dashboard/DashboardSection';
import { AgentSection } from './components/Chat/AgentSection';
import { mockCustomer } from './data/mockCustomer';
import type { CustomerProfile } from './data/mockCustomer';
import { fetchCustomerProfile } from './lib/api';

export default function App() {
  const [profile, setProfile] = useState<CustomerProfile | null>(null);
  const [profileError, setProfileError] = useState(false);

  useEffect(() => {
    let active = true;
    fetchCustomerProfile()
      .then((customer) => {
        if (active) setProfile(customer);
      })
      .catch(() => {
        if (active) {
          setProfile(mockCustomer);
          setProfileError(true);
        }
      });
    return () => {
      active = false;
    };
  }, []);

  return (
    <Box sx={{ minHeight: '100vh' }}>
      <Header />
      <Container maxWidth="lg" sx={{ py: { xs: 3, sm: 5 } }}>
        {profileError && (
          <Alert severity="warning" sx={{ mb: 3 }}>
            Live customer data is unavailable, so the dashboard is showing demo data.
          </Alert>
        )}
        <Grid container spacing={{ xs: 4, md: 5 }}>
          <Grid item xs={12} md={6}>
            {profile ? <DashboardSection profile={profile} /> : <CircularProgress aria-label="Loading customer profile" />}
          </Grid>
          <Grid item xs={12} md={6}>
            <AgentSection />
          </Grid>
        </Grid>
      </Container>
    </Box>
  );
}
