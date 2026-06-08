import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { GoogleOAuthProvider } from '@react-oauth/google';
import App from './App';
import './index.css';
import { useThemeStore } from './stores/themeStore';
import { useAuthStore } from './stores/authStore';
import { localPlatform } from './api/localPlatform';

useThemeStore.getState().init();
useAuthStore.getState().init();
localPlatform.init();

const googleClientId = import.meta.env.VITE_GOOGLE_CLIENT_ID as string | undefined;

const app = (
  <StrictMode>
    <App />
  </StrictMode>
);

createRoot(document.getElementById('root')!).render(
  googleClientId ? <GoogleOAuthProvider clientId={googleClientId}>{app}</GoogleOAuthProvider> : app,
);
