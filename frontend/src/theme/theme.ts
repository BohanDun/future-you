import { createTheme } from '@mui/material/styles';

// ---------------------------------------------------------------------------
// Future You — design tokens
//
// Concept: "Future You" is a horizon — the line between where your money
// stands today and where it's headed. The palette is a cool paper background
// (not the warm-cream default) with two accents pulled from that horizon:
// a brass "sunrise" gold for forward motion, and a deep teal for stability.
// Risk reads through a dedicated traffic-light trio so it never gets
// confused with brand color.
// ---------------------------------------------------------------------------

export const colors = {
  ink: '#121A2A', // near-black navy — primary text
  inkSoft: '#4B5568', // secondary text
  paper: '#EFF3F4', // page background — cool, not cream
  surface: '#FFFFFF', // card background
  line: '#DEE4E3', // hairline dividers
  horizonGold: '#C8963B', // brand accent — forward motion, "future"
  horizonGoldSoft: '#F4E7CE',
  futureTeal: '#1E6B67', // brand accent — stability, growth
  futureTealSoft: '#DCEDEA',
  riskLow: '#1E6B67',
  riskLowSoft: '#DCEDEA',
  riskMedium: '#C8963B',
  riskMediumSoft: '#F4E7CE',
  riskHigh: '#B3462F',
  riskHighSoft: '#F6DFD8',
};

export const theme = createTheme({
  palette: {
    mode: 'light',
    background: {
      default: colors.paper,
      paper: colors.surface,
    },
    text: {
      primary: colors.ink,
      secondary: colors.inkSoft,
    },
    primary: {
      main: colors.horizonGold,
      contrastText: colors.ink,
    },
    secondary: {
      main: colors.futureTeal,
      contrastText: '#FFFFFF',
    },
    divider: colors.line,
  },
  typography: {
    fontFamily: '"Inter", "Helvetica Neue", Arial, sans-serif',
    h1: {
      fontFamily: '"Fraunces", Georgia, serif',
      fontWeight: 600,
      letterSpacing: '-0.01em',
    },
    h2: {
      fontFamily: '"Fraunces", Georgia, serif',
      fontWeight: 600,
      letterSpacing: '-0.01em',
    },
    h3: {
      fontFamily: '"Fraunces", Georgia, serif',
      fontWeight: 600,
    },
    h4: {
      fontFamily: '"Fraunces", Georgia, serif',
      fontWeight: 600,
    },
    h5: {
      fontFamily: '"Fraunces", Georgia, serif',
      fontWeight: 600,
    },
    h6: {
      fontFamily: '"Inter", sans-serif',
      fontWeight: 700,
      textTransform: 'uppercase',
      letterSpacing: '0.06em',
      fontSize: '0.75rem',
    },
    button: {
      textTransform: 'none',
      fontWeight: 600,
    },
  },
  shape: {
    borderRadius: 14,
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 10,
          boxShadow: 'none',
        },
        containedPrimary: {
          color: colors.ink,
          '&:hover': { boxShadow: 'none' },
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundImage: 'none',
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          border: `1px solid ${colors.line}`,
          boxShadow: 'none',
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          fontWeight: 600,
        },
      },
    },
  },
});

export const numericFont = '"IBM Plex Mono", monospace';
