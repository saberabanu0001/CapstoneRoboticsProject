import AsyncStorage from "@react-native-async-storage/async-storage";
import * as Linking from "expo-linking";
import * as WebBrowser from "expo-web-browser";
import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

import { CLOUD_API_BASE_URL, CLOUD_AUTH_START_PATH } from "@/constants/env";
import { fetchCurrentSession } from "@/services/cloud-api";
import type { CloudSession, CloudUser } from "@/types/cloud";

const CLOUD_SESSION_STORAGE_KEY = "cloud_session_v1";

interface AuthContextValue {
  user: CloudUser | null;
  sessionToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  authError: string | null;
  signIn: () => Promise<void>;
  signOut: () => Promise<void>;
  refreshSession: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

const persistSession = async (session: CloudSession | null) => {
  try {
    if (!session) {
      await AsyncStorage.removeItem(CLOUD_SESSION_STORAGE_KEY);
      return;
    }

    await AsyncStorage.setItem(
      CLOUD_SESSION_STORAGE_KEY,
      JSON.stringify(session)
    );
  } catch (error) {
    console.warn("Failed to persist auth session", error);
  }
};

const restoreSession = async (): Promise<CloudSession | null> => {
  try {
    const stored = await AsyncStorage.getItem(CLOUD_SESSION_STORAGE_KEY);
    if (!stored) {
      return null;
    }

    const parsed = JSON.parse(stored) as CloudSession;
    if (!parsed?.token) {
      return null;
    }

    return parsed;
  } catch (error) {
    console.warn("Failed to restore auth session", error);
    return null;
  }
};

const extractSessionToken = (url: string): string | null => {
  const parsed = Linking.parse(url);
  const params = parsed.queryParams ?? {};

  const candidates = [
    typeof params.token === "string" ? params.token : null,
    typeof params.sessionToken === "string" ? params.sessionToken : null,
    typeof params.session_token === "string" ? params.session_token : null,
  ].filter((value): value is string => Boolean(value));

  return candidates[0] ?? null;
};

const buildAuthUrl = (redirectUri: string) => {
  if (!CLOUD_API_BASE_URL) {
    throw new Error(
      "Cloud API base URL is not configured. Set EXPO_PUBLIC_CLOUD_API_BASE_URL."
    );
  }

  const url = new URL(CLOUD_AUTH_START_PATH, CLOUD_API_BASE_URL);
  url.searchParams.set("redirect_uri", redirectUri);
  return url.toString();
};

export const AuthProvider = ({ children }: React.PropsWithChildren) => {
  const [session, setSession] = useState<CloudSession | null>(null);
  const [isRestoring, setIsRestoring] = useState(true);
  const [isAuthenticating, setIsAuthenticating] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    (async () => {
      const restored = await restoreSession();
      if (cancelled) {
        return;
      }

      if (restored) {
        setSession(restored);
        try {
          const refreshed = await fetchCurrentSession(restored.token);
          if (cancelled) {
            return;
          }
          setSession(refreshed);
          setAuthError(null);
          await persistSession(refreshed);
        } catch (error) {
          if (!cancelled) {
            const message =
              error instanceof Error
                ? error.message
                : "Failed to refresh saved session.";
            setAuthError(message);
          }
        }
      }

      if (!cancelled) {
        setIsRestoring(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  const signOut = useCallback(async () => {
    setSession(null);
    setAuthError(null);
    await persistSession(null);
  }, []);

  const refreshSession = useCallback(async () => {
    if (!session?.token) {
      return;
    }

    try {
      const refreshed = await fetchCurrentSession(session.token);
      setSession(refreshed);
      setAuthError(null);
      await persistSession(refreshed);
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : "Failed to refresh session.";
      setAuthError(message);
      await signOut();
      throw error instanceof Error ? error : new Error(message);
    }
  }, [session?.token, signOut]);

  const signIn = useCallback(async () => {
    setAuthError(null);

    setIsAuthenticating(true);

    try {
      const redirectUri = Linking.createURL("auth-callback");
      const authUrl = buildAuthUrl(redirectUri);

      await WebBrowser.warmUpAsync();

      const result = await WebBrowser.openAuthSessionAsync(
        authUrl,
        redirectUri
      );

      if (result.type !== "success" || !result.url) {
        if (result.type === "cancel") {
          throw new Error("Sign-in cancelled.");
        }
        throw new Error("Sign-in was not completed.");
      }

      const token = extractSessionToken(result.url);
      if (!token) {
        throw new Error("No session token returned from authentication.");
      }

      const refreshed = await fetchCurrentSession(token);
      setSession(refreshed);
      setAuthError(null);
      await persistSession(refreshed);
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Failed to sign in.";
      setAuthError(message);
      throw error instanceof Error ? error : new Error(message);
    } finally {
      setIsAuthenticating(false);
      try {
        await WebBrowser.coolDownAsync();
      } catch (error) {
        console.warn("Failed to cool down auth session", error);
      }
    }
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user: session?.user ?? null,
      sessionToken: session?.token ?? null,
      isAuthenticated: Boolean(session?.token),
      isLoading: isRestoring || isAuthenticating,
      authError,
      signIn,
      signOut,
      refreshSession,
    }),
    [
      authError,
      isAuthenticating,
      isRestoring,
      refreshSession,
      session?.token,
      session?.user,
      signIn,
      signOut,
    ]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }

  return context;
};
