import AsyncStorage from "@react-native-async-storage/async-storage";
import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import { getDeviceId } from "@/services/device-id";
import {
  RobotAPI,
  RobotNetworkInfo,
  RobotStatus,
  createRobotApi,
} from "@/services/robot-api";
import { getStoredRobotByUrl, updateRobotLastIp, updateRobotLastSeen } from "@/services/robot-storage";

const isIpv4Address = (value: string | null | undefined) => {
  if (!value) {
    return false;
  }

  const segments = value.split(".");
  if (segments.length !== 4) {
    return false;
  }

  return segments.every((segment) => {
    if (segment.trim() === "") {
      return false;
    }
    const numeric = Number(segment);
    return Number.isInteger(numeric) && numeric >= 0 && numeric <= 255;
  });
};

const deriveIpv4FromUrl = (value: string) => {
  try {
    const parsed = new URL(value.includes("://") ? value : `http://${value}`);
    return isIpv4Address(parsed.hostname) ? parsed.hostname : null;
  } catch (error) {
    console.warn("Failed to parse robot base URL for IPv4 fallback", value, error);
    return null;
  }
};

interface RobotContextValue {
  api: RobotAPI;
  baseUrl: string;
  setBaseUrl: (url: string) => void;
  status: RobotStatus | null;
  statusError: string | null;
  lastUpdated?: Date;
  isPolling: boolean;
  setIsPolling: (value: boolean) => void;
  refreshStatus: () => Promise<void>;
  sessionId: string | null;
  setSessionId: (sessionId: string | null) => Promise<void>;
  clearConnection: () => Promise<void>;
  connectToStoredRobot: (baseUrl: string) => Promise<boolean>;
  currentRobotId: string | null;
  setCurrentRobotId: (robotId: string | null) => void;
}

const RobotContext = createContext<RobotContextValue | undefined>(undefined);

const SECURE_STORE_CONTROL_TOKEN_KEY = "robot_control_token";

export const ROBOT_BASE_URL_STORAGE_KEY = "robot_base_url";
export const ROBOT_SESSION_ID_STORAGE_KEY = "robot_session_id";
export const DEFAULT_ROBOT_BASE_URL = "http://192.168.200.123:8000";

export const RobotProvider = ({ children }: React.PropsWithChildren) => {
  const [baseUrl, setBaseUrlState] = useState<string>(DEFAULT_ROBOT_BASE_URL);
  const [status, setStatus] = useState<RobotStatus | null>(null);
  const [statusError, setStatusError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | undefined>(undefined);
  const [isPolling, setIsPolling] = useState<boolean>(true);
  const hasPollingBeenPausedRef = useRef(false);
  const [sessionId, setSessionIdState] = useState<string | null>(null);
  const [currentRobotId, setCurrentRobotId] = useState<string | null>(null);

  const api = useMemo(
    () => createRobotApi(baseUrl, undefined, sessionId),
    [baseUrl, sessionId]
  );

  const refreshStatus = useCallback(async () => {
    try {
      console.log("Refreshing robot status from", baseUrl);
      const health = await api.fetchHealth();

      // Update last seen for stored robot if we have a robot_id
      if (currentRobotId) {
        await updateRobotLastSeen(currentRobotId).catch((err) => {
          console.warn("Failed to update robot last seen", err);
        });
      }

      const [networkInfo, telemetry, mode] = await Promise.all([
        api
          .fetchNetworkInfo()
          .catch((error) => {
            console.warn("Failed to load robot network info", error);
            return null;
          }),
        api
          .fetchTelemetry()
          .catch((error) => {
            console.warn("Failed to load robot telemetry", error);
            return null;
          }),
        api
          .fetchMode()
          .catch((error) => {
            console.warn("Failed to load robot mode", error);
            return null;
          }),
      ]);

      const mergedNetwork: RobotNetworkInfo | undefined = (() => {
        const sources: (RobotNetworkInfo | null | undefined)[] = [
          health?.network,
          telemetry?.network,
          networkInfo,
        ];

        const aggregated: RobotNetworkInfo = {};
        for (const source of sources) {
          if (!source) {
            continue;
          }
          Object.assign(aggregated, source);
          if (source.ssid && !aggregated.wifiSsid) {
            aggregated.wifiSsid = source.ssid;
          }
        }

        return Object.keys(aggregated).length ? aggregated : undefined;
      })();

      const baseUrlIpv4 = deriveIpv4FromUrl(baseUrl);

      const combinedNetwork: RobotNetworkInfo | undefined = (() => {
        const network: RobotNetworkInfo = mergedNetwork
          ? { ...mergedNetwork }
          : {};

        if (!network.ip && baseUrlIpv4) {
          network.ip = baseUrlIpv4;
        }

        // Update stored robot's last IP if we have a robot_id
        if (currentRobotId && network.ip) {
          updateRobotLastIp(currentRobotId, network.ip).catch((err) => {
            console.warn("Failed to update robot last IP", err);
          });
        }

        return Object.keys(network).length ? network : undefined;
      })();

      // Get battery from multiple possible fields (API returns battery_percent)
      const batteryValue = telemetry?.battery_percent ?? telemetry?.battery ?? health?.battery;
      console.log("Battery debug:", {
        telemetryBatteryPercent: telemetry?.battery_percent,
        telemetryBattery: telemetry?.battery,
        healthBattery: health?.battery,
        finalBattery: batteryValue,
        telemetryExists: telemetry !== null,
        healthExists: health !== null,
      });

      const combined: RobotStatus = {
        health,
        telemetry: telemetry ?? undefined,
        network: combinedNetwork,
        battery: batteryValue,
        cpuLoad: telemetry?.cpuLoad,
        temperatureC: telemetry?.temperatureC,
        humidity: telemetry?.humidity,
        uptimeSeconds: telemetry?.uptimeSeconds ?? health?.uptimeSeconds,
        mode:
          mode?.mode ?? mode?.current ?? mode?.status ?? combinedNetwork?.mode,
        gesture: telemetry?.gesture,
        gesture_confidence: telemetry?.gesture_confidence,
      };

      setStatus(combined);
      setLastUpdated(new Date());
      setStatusError(null);
      console.log("Robot status updated", combined);
    } catch (error) {
      console.warn("Failed to refresh robot status", error);
      setStatus(null);
      setStatusError((error as Error).message);
    }
  }, [api, baseUrl, currentRobotId]);

  useEffect(() => {
    let isMounted = true;
    (async () => {
      try {
        const storedUrl = await AsyncStorage.getItem(
          ROBOT_BASE_URL_STORAGE_KEY
        );
        if (storedUrl && isMounted) {
          console.log("Loaded stored robot base URL", storedUrl);
          setBaseUrlState(storedUrl);
        }
        const storedSessionId = await AsyncStorage.getItem(
          ROBOT_SESSION_ID_STORAGE_KEY
        );
        if (storedSessionId && isMounted) {
          setSessionIdState(storedSessionId);
        }
      } catch (error) {
        console.warn("Failed to load stored robot base URL", error);
      }

      try {
        // Check if SecureStore is available (it may not be on web or in some dev environments)
        if (SecureStore.isAvailableAsync && !(await SecureStore.isAvailableAsync())) {
          console.warn("SecureStore is not available on this platform");
        } else {
          const storedToken = await SecureStore.getItemAsync(
            CONTROL_TOKEN_STORAGE_KEY
          );
          if (storedToken && isMounted) {
            console.log("Loaded stored control token");
            setControlTokenState(storedToken);
          }
        }
      } catch (error) {
        console.warn("Failed to load stored control token", error);
        // Don't crash the app if SecureStore fails - it might not be available in dev mode
      }
    })();

    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    if (!isPolling) {
      hasPollingBeenPausedRef.current = true;
      return;
    }

    if (!hasPollingBeenPausedRef.current) {
      return;
    }

    void refreshStatus();
    const interval = setInterval(() => {
      void refreshStatus();
    }, 10_000);

    return () => {
      clearInterval(interval);
    };
  }, [isPolling, refreshStatus]);

  const setBaseUrl = useCallback(
    (url: string) => {
      const normalized = url.replace(/\/$/, "");
      console.log("Updating robot base URL", {
        previous: baseUrl,
        next: normalized,
      });
      api.updateBaseUrl(normalized);
      setBaseUrlState(normalized);
      setStatusError(null);
      void AsyncStorage.setItem(ROBOT_BASE_URL_STORAGE_KEY, normalized).catch(
        (error) => {
          console.warn("Failed to persist robot base URL", error);
        }
      );
    },
    [api, baseUrl]
  );

  const setControlToken = useCallback(
    async (token: string | null) => {
      console.log("Updating control token", { hasToken: Boolean(token) });
      api.setControlToken(token);
      setControlTokenState(token);
      try {
        // Check if SecureStore is available
        if (SecureStore.isAvailableAsync && !(await SecureStore.isAvailableAsync())) {
          console.warn("SecureStore is not available, token will not persist");
          return;
        }
        if (token) {
          await SecureStore.setItemAsync(CONTROL_TOKEN_STORAGE_KEY, token);
        } else {
          await SecureStore.deleteItemAsync(CONTROL_TOKEN_STORAGE_KEY);
        }
      } catch (error) {
        console.warn("Failed to persist control token", error);
        // Don't throw - token is still set in memory even if storage fails
      }
    },
    [api]
  );

  const setSessionId = useCallback(
    async (sessionIdValue: string | null) => {
      console.log("Updating session ID", { hasSession: Boolean(sessionIdValue) });
      api.setSessionId(sessionIdValue);
      setSessionIdState(sessionIdValue);

      try {
        if (sessionIdValue) {
          await AsyncStorage.setItem(
            ROBOT_SESSION_ID_STORAGE_KEY,
            sessionIdValue
          );
        } else {
          await AsyncStorage.removeItem(ROBOT_SESSION_ID_STORAGE_KEY);
        }
      } catch (error) {
        console.warn("Failed to persist session ID", error);
      }
    },
    [api]
  );

  const connectToStoredRobot = useCallback(
    async (url: string): Promise<boolean> => {
      try {
        const storedRobot = await getStoredRobotByUrl(url);
        if (!storedRobot) {
          console.log("No stored robot found for URL:", url);
          return false;
        }

        // Verify device_id matches
        const currentDeviceId = await getDeviceId();
        if (storedRobot.device_id !== currentDeviceId) {
          console.log("Device ID mismatch, cannot use stored robot");
          return false;
        }

        console.log("Found stored robot, connecting:", storedRobot.robot_id);

        // Set up connection with stored credentials
        setBaseUrlState(storedRobot.baseUrl);
        api.updateBaseUrl(storedRobot.baseUrl);
        setCurrentRobotId(storedRobot.robot_id);

        // Update last seen
        await updateRobotLastSeen(storedRobot.robot_id);
        if (storedRobot.last_ip) {
          await updateRobotLastIp(storedRobot.robot_id, storedRobot.last_ip);
        }

        // Try to refresh status to verify connection
        try {
          await refreshStatus();
          console.log("Successfully connected to stored robot");
          return true;
        } catch (error) {
          console.warn("Failed to verify stored robot connection", error);
          // Still return true - the connection might work, just status check failed
          return true;
        }
      } catch (error) {
        console.error("Failed to connect to stored robot", error);
        return false;
      }
    },
    [api, refreshStatus]
  );

  const clearConnection = useCallback(async () => {
    console.log("Clearing robot connection");
    // Clear status and error
    setStatus(null);
    setStatusError(null);
    setLastUpdated(undefined);

    // Reset base URL to default
    setBaseUrlState(DEFAULT_ROBOT_BASE_URL);
    api.updateBaseUrl(DEFAULT_ROBOT_BASE_URL);

    // Clear session ID
    setSessionIdState(null);
    api.setSessionId(null);

    // Clear current robot ID
    setCurrentRobotId(null);

    // Clear stored values
    try {
      await AsyncStorage.removeItem(ROBOT_BASE_URL_STORAGE_KEY);
      await AsyncStorage.removeItem(ROBOT_SESSION_ID_STORAGE_KEY);
    } catch (error) {
      console.warn("Failed to clear stored base URL", error);
    }

    try {
      if (SecureStore.isAvailableAsync && await SecureStore.isAvailableAsync()) {
        await SecureStore.deleteItemAsync(CONTROL_TOKEN_STORAGE_KEY);
      }
    } catch (error) {
      console.warn("Failed to clear stored control token", error);
    }
  }, [api]);

  const value = useMemo(
    () => ({
      api,
      baseUrl,
      setBaseUrl,
      status,
      statusError,
      lastUpdated,
      isPolling,
      setIsPolling,
      refreshStatus,
      sessionId,
      setSessionId,
      clearConnection,
      connectToStoredRobot,
      currentRobotId,
      setCurrentRobotId,
    }),
    [
      api,
      baseUrl,
      isPolling,
      lastUpdated,
      refreshStatus,
      status,
      statusError,
      setSessionId,
      clearConnection,
      connectToStoredRobot,
      sessionId,
      currentRobotId,
    ]
  );

  return (
    <RobotContext.Provider value={value}>{children}</RobotContext.Provider>
  );
};

export const useRobot = () => {
  const context = useContext(RobotContext);
  if (!context) {
    throw new Error("useRobot must be used within a RobotProvider");
  }

  return context;
};
