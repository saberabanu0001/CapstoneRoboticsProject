const WS_PATH = "/json";

export const cmd_movition_ctrl = 1;
export const cmd_pwm_ctrl = 11;
export const max_speed = 0.65;
export const slow_speed = 0.3;
export const max_rate = 1.0;
export const mid_rate = 0.66;
export const min_rate = 0.3;
export const speed_rate = max_rate;
export const cmd_lights_ctrl = 132;
export const cmd_gimbal_ctrl = 133;

export interface MovementCommand {
  T: number;
  L: number;
  R: number;
}

export interface LightsCommand {
  T: number;
  IO4: number;
  IO5: number;
}

export interface GimbalCommand {
  T: number;
  X: number;
  Y: number;
  SPD: number;
}

let heartbeat_left = 0;
let heartbeat_right = 0;
let socketJson: WebSocket | null = null;
let activeSocketUrl: string | null = null;

const buildSocketUrl = (baseUrl?: string | null) => {
  const normalizeBaseUrl = () => {
    if (baseUrl && baseUrl.trim()) {
      return baseUrl.startsWith("http") ? baseUrl : `http://${baseUrl}`;
    }

    if (typeof location !== "undefined" && location.host) {
      return `${location.protocol || "http:"}//${location.host}`;
    }

    return null;
  };

  const normalized = normalizeBaseUrl();
  if (!normalized) {
    return null;
  }

  try {
    const parsedUrl = new URL(normalized);
    const host = parsedUrl.hostname;
    const isIp = /^\d{1,3}(\.\d{1,3}){3}$/.test(host) || host === "localhost";

    parsedUrl.protocol = isIp
      ? "ws:"
      : parsedUrl.protocol === "https:"
      ? "wss:"
      : "ws:";

    parsedUrl.pathname = `${parsedUrl.pathname.replace(/\/$/, "")}${WS_PATH}`;
    parsedUrl.search = "";

    return parsedUrl.toString();
  } catch (error) {
    console.warn("Failed to derive json WebSocket URL", normalized, error);
    return null;
  }
};

const ensureSocket = (baseUrl?: string | null) => {
  const url = buildSocketUrl(baseUrl);
  if (!url) {
    console.warn("Unable to determine json WebSocket URL");
    return null;
  }

  if (socketJson && activeSocketUrl === url) {
    if (
      socketJson.readyState !== WebSocket.CLOSED &&
      socketJson.readyState !== WebSocket.CLOSING
    ) {
      return socketJson;
    }
  }

  if (socketJson) {
    try {
      socketJson.close();
    } catch (error) {
      console.warn("Failed to close existing json WebSocket", error);
    }
  }

  try {
    socketJson = new WebSocket(url);
    activeSocketUrl = url;

    socketJson.onerror = (event) => {
      console.warn("json WebSocket error", event);
    };

    socketJson.onclose = (event) => {
      console.warn("json WebSocket closed", event.code, event.reason);
    };
  } catch (error) {
    console.warn("Failed to establish json WebSocket", error);
    socketJson = null;
  }

  return socketJson;
};

export const cmdJsonCmd = (
  jsonData: MovementCommand | LightsCommand | GimbalCommand,
  baseUrl?: string | null
) => {
  const socket = ensureSocket(baseUrl);
  if (!socket) {
    return;
  }

  if (jsonData.T === cmd_movition_ctrl) {
    const movementData = jsonData as MovementCommand;
    heartbeat_left = movementData.L;
    heartbeat_right = movementData.R;
  }

  let payload: MovementCommand | LightsCommand | GimbalCommand;
  
  if (jsonData.T === cmd_movition_ctrl) {
    payload = {
      ...jsonData,
      L: heartbeat_left * speed_rate,
      R: heartbeat_right * speed_rate,
    } as MovementCommand;
  } else {
    payload = jsonData;
  }

  const sendPayload = () => {
    try {
      socket.send(JSON.stringify(payload));
    } catch (error) {
      console.warn("Failed to send json command", error);
    }
  };

  if (socket.readyState === WebSocket.OPEN) {
    sendPayload();
  } else if (socket.readyState === WebSocket.CONNECTING) {
    socket.addEventListener("open", sendPayload, { once: true });
  } else {
    // Attempt to re-establish and send when opened.
    const reopened = ensureSocket(baseUrl);
    if (reopened) {
      if (reopened.readyState === WebSocket.OPEN) {
        sendPayload();
      } else if (reopened.readyState === WebSocket.CONNECTING) {
        reopened.addEventListener("open", sendPayload, { once: true });
      }
    }
  }
};
