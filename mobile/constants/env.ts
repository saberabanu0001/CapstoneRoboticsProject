const readEnv = (key: string): string | null => {
  const value = process.env[key];
  if (!value) {
    return null;
  }

  const trimmed = value.trim();
  return trimmed.length ? trimmed : null;
};

export const CLOUD_API_BASE_URL = readEnv("EXPO_PUBLIC_CLOUD_API_BASE_URL");
export const CLOUD_WS_BASE_URL = readEnv("EXPO_PUBLIC_CLOUD_WS_BASE_URL");
export const CLOUD_AUTH_START_PATH =
  readEnv("EXPO_PUBLIC_CLOUD_AUTH_START_PATH") ?? "/auth/google/start";

export const CLOUD_DISCOVERY_REFRESH_INTERVAL_MS = 15_000;

export const isCloudConfigured = () => Boolean(CLOUD_API_BASE_URL);
