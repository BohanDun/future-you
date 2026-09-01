import { Amplify } from 'aws-amplify';
import {
  confirmSignUp,
  fetchAuthSession,
  getCurrentUser,
  signIn,
  signOut,
  signUp,
} from 'aws-amplify/auth';

export const authEnabled = import.meta.env.VITE_AUTH_MODE === 'cognito';

const userPoolId = import.meta.env.VITE_COGNITO_USER_POOL_ID;
const userPoolClientId = import.meta.env.VITE_COGNITO_USER_POOL_CLIENT_ID;

export const authConfigurationError = authEnabled && (!userPoolId || !userPoolClientId)
  ? 'AWS sign-in is not configured. Set VITE_COGNITO_USER_POOL_ID and '
    + 'VITE_COGNITO_USER_POOL_CLIENT_ID, then restart the frontend. '
    + 'See docs/AWS_AUTH_SETUP.md.'
  : null;

if (authEnabled && userPoolId && userPoolClientId) {
  Amplify.configure({
    Auth: {
      Cognito: {
        userPoolId,
        userPoolClientId,
      },
    },
  });
}

export async function currentAuthenticatedUser() {
  if (!authEnabled || authConfigurationError) return null;
  try {
    return await getCurrentUser();
  } catch {
    return null;
  }
}

export async function registerUser(email: string, password: string) {
  return signUp({
    username: email.trim().toLowerCase(),
    password,
    options: {
      userAttributes: { email: email.trim().toLowerCase() },
    },
  });
}

export async function confirmRegisteredUser(email: string, code: string) {
  return confirmSignUp({
    username: email.trim().toLowerCase(),
    confirmationCode: code.trim(),
  });
}

export async function loginUser(email: string, password: string) {
  return signIn({
    username: email.trim().toLowerCase(),
    password,
  });
}

export async function logoutUser() {
  await signOut();
}

export async function getAccessToken(): Promise<string | null> {
  if (!authEnabled) return null;
  const session = await fetchAuthSession();
  return session.tokens?.accessToken?.toString() ?? null;
}
