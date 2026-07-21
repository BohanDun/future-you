import { createContext } from 'react';
import type { AuthUser } from 'aws-amplify/auth';

export interface AuthContextValue {
  enabled: boolean;
  loading: boolean;
  user: AuthUser | null;
  refresh: () => Promise<void>;
  logout: () => Promise<void>;
}

export const AuthContext = createContext<AuthContextValue | null>(null);
