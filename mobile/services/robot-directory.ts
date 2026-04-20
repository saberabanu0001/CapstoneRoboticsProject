import { CLOUD_API_BASE_URL, CLOUD_WS_BASE_URL } from "@/constants/env";
import type { NearbyRobotSummary } from "@/types/cloud";

export type NearbyRobotsMessage =
  | NearbyRobotSummary[]
  | {
      type?: string;
      robots?: NearbyRobotSummary[];
      robot?: NearbyRobotSummary;
    };

const buildWebSocketUrl = (path: string) => {
  const base = CLOUD_WS_BASE_URL ?? CLOUD_API_BASE_URL;
  if (!base) {
    throw new Error(
      "Cloud WebSocket base URL is not configured. Set EXPO_PUBLIC_CLOUD_WS_BASE_URL or EXPO_PUBLIC_CLOUD_API_BASE_URL."
    );
  }

  const parsed = new URL(base);
  if (parsed.protocol === "http:") {
    parsed.protocol = "ws:";
  } else if (parsed.protocol === "https:") {
    parsed.protocol = "wss:";
  }

  parsed.pathname = path;
  parsed.search = "";
  parsed.hash = "";
  return parsed.toString();
};

const normalizeNearbyList = (
  message: NearbyRobotsMessage
): NearbyRobotSummary[] | null => {
  if (Array.isArray(message)) {
    return message;
  }

  if (message.robots && Array.isArray(message.robots)) {
    return message.robots;
  }

  if (message.robot) {
    return [message.robot];
  }

  return null;
};

export interface NearbyRobotsSocketHandlers {
  onSnapshot: (robots: NearbyRobotSummary[]) => void;
  onError?: (error: Error) => void;
  onClose?: () => void;
}

export const connectNearbyRobotsSocket = (
  token: string,
  handlers: NearbyRobotsSocketHandlers
) => {
  const url = new URL(buildWebSocketUrl("/robots/nearby"));
  url.searchParams.set("token", token);

  const socket = new WebSocket(url.toString());

  socket.onmessage = (event) => {
    try {
      const payload = JSON.parse(event.data) as NearbyRobotsMessage;
      const list = normalizeNearbyList(payload);
      if (list && list.length) {
        handlers.onSnapshot(list);
      }
    } catch (error) {
      console.warn("Failed to parse nearby robot message", error);
      handlers.onError?.(
        error instanceof Error
          ? error
          : new Error("Unable to decode nearby robot update.")
      );
    }
  };

  socket.onerror = (event) => {
    const message =
      typeof event === "object" && event && "message" in event
        ? String((event as { message?: unknown }).message ?? "Nearby robot socket error.")
        : "Nearby robot socket error.";
    handlers.onError?.(new Error(message));
  };

  socket.onclose = () => {
    handlers.onClose?.();
  };

  return () => {
    try {
      socket.close();
    } catch (error) {
      console.warn("Failed to close nearby robot socket", error);
    }
  };
};
