import { Box, Container, Grid } from '@mui/material';
import { Header } from './components/Layout/Header';
import { DashboardSection } from './components/Dashboard/DashboardSection';
import { AgentSection } from './components/Chat/AgentSection';
import { mockCustomer } from './data/mockCustomer';

export default function App() {
  return (
    <Box sx={{ minHeight: '100vh' }}>
      <Header />
      <Container maxWidth="lg" sx={{ py: { xs: 3, sm: 5 } }}>
        <Grid container spacing={{ xs: 4, md: 5 }}>
          <Grid item xs={12} md={6}>
            <DashboardSection profile={mockCustomer} />
          </Grid>
          <Grid item xs={12} md={6}>
            <AgentSection />
          </Grid>
        </Grid>
      </Container>
    </Box>
  );
}
