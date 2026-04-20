import { Redirect, useLocalSearchParams } from 'expo-router';
import React, { useEffect } from 'react';

import { useAuth } from '@/context/auth-provider';

export default function AuthCallbackScreen() {
  const params = useLocalSearchParams<Record<string, string>>();
  const { sessionToken, refreshSession } = useAuth();

  useEffect(() => {
    if (!params || sessionToken) {
      return;
    }

    const tokenParam =
      params.token || params.sessionToken || params.session_token;
    if (!tokenParam) {
      return;
    }

    void refreshSession();
  }, [params, refreshSession, sessionToken]);

  return <Redirect href="/connection" />;
}
