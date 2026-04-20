import axios, { AxiosError, AxiosInstance, AxiosResponse } from "axios";

export type RobotConnectionState =
  | "disconnected"
  | "connecting"
  | "connected"
  | "error";

export interface WifiCredentials {
  ssid: string;
  password: string;
}

export interface RobotNetworkInfo {
  ip?: string;
  ssid?: string;
  wifiSsid?: string;
  network_name?: string;
  connected?: boolean;
  signalStrength?: number;
  availableNetworks?: string[];
  mode?: string;
  [key: string]: unknown;
}

export interface RobotHealth {
  connected?: boolean;
  firmware?: Record<string, unknown>;
  battery?: number;
  uptimeSeconds?: number;
  network?: RobotNetworkInfo;
  [key: string]: unknown;
}

export interface RobotTelemetry {
  battery?: number;
  battery_percent?: number;
  battery_voltage?: number;
  cpuLoad?: number;
  temperatureC?: number;
  temperature?: number;
  humidity?: number;
  uptimeSeconds?: number;
  network?: RobotNetworkInfo;
  gesture?: 'like' | 'heart' | 'none';
  gesture_confidence?: number;
  [key: string]: unknown;
}

export interface CameraCaptureMetadata {
  id?: string;
  url?: string;
  snapshotUrl?: string;
  imageUrl?: string;
  path?: string;
  saved?: boolean;
  [key: string]: unknown;
}

export interface RobotModeState {
  mode?: string;
  current?: string;
  status?: string;
  [key: string]: unknown;
}

export interface RobotStatus {
  health?: RobotHealth;
  telemetry?: RobotTelemetry;
  network?: RobotNetworkInfo;
  battery?: number;
  cpuLoad?: number;
  temperatureC?: number;
  humidity?: number;
  uptimeSeconds?: number;
  mode?: string;
  [key: string]: unknown;
}

export interface WifiNetwork {
  ssid: string;
  signal_strength?: number;
  security?: string;
  frequency?: number;
}

export interface WifiScanResponse {
  networks: WifiNetwork[] | string[];
}

export interface ClaimRequestResponse {
  success?: boolean;
  [key: string]: unknown;
}

export interface ClaimConfirmResponse {
  success?: boolean;
  controlToken?: string;
  control_token?: string;
  sessionId?: string;
  session_id?: string;
  session?: string;
  robot_id?: string;
  device_id?: string;
  [key: string]: unknown;
}

export interface RobotApiOptions {
  baseUrl: string;
  timeout?: number;
  sessionId?: string | null;
  axiosInstance?: AxiosInstance;
}

interface ApiResponse<T = any> {
  data?: T;
  error?: string;
  status: number;
}

interface ErrorResponse {
  message?: string;
  error?: string;
}

export class RobotAPI {
  private baseUrl: string;
  private axiosInstance: AxiosInstance;
  private timeout: number;
  private sessionId: string | null;

  constructor(options: RobotApiOptions) {
    this.baseUrl = options.baseUrl.replace(/\/$/, "");
    this.timeout = options.timeout ?? 5000;
    this.sessionId = options.sessionId ?? null;

    this.axiosInstance =
      options.axiosInstance ??
      axios.create({
        baseURL: this.baseUrl,
        timeout: this.timeout,
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",

          ...(this.sessionId ? { "session-id": this.sessionId } : {}),
        },
      });

    // Request interceptor to add auth headers
    this.axiosInstance.interceptors.request.use(
      (config) => {
        console.log(
          "Request interceptor - Method:",
          config.method,
          "URL:",
          config.url
        );

        // CRITICAL: Ensure method is preserved and uppercase
        if (config.method) {
          config.method = config.method.toUpperCase() as any;
        }

        if (this.sessionId) {
          config.headers["session-id"] = this.sessionId;
        }

        console.log("Request interceptor - Final method:", config.method);
        return config;
      },
      (error) => {
        return Promise.reject(error);
      }
    );

    // Response interceptor for error handling
    this.axiosInstance.interceptors.response.use(
      (response: AxiosResponse) => {
        console.log("Response received:", {
          status: response.status,
          method: response.config.method,
          url: response.config.url,
        });
        return response;
      },
      (error: AxiosError) => {
        console.log("Response error:", {
          status: error.response?.status,
          method: error.config?.method,
          url: error.config?.url,
          data: error.config?.data,
        });
        return Promise.reject(error);
      }
    );
  }

  public updateBaseUrl(baseUrl: string) {
    this.baseUrl = baseUrl.replace(/\/$/, "");
    this.axiosInstance.defaults.baseURL = this.baseUrl;
  }

  public getBaseUrl(): string {
    return this.baseUrl;
  }

  public setSessionId(sessionId: string | null) {
    this.sessionId = sessionId;
  }

  public getSessionId(): string | null {
    return this.sessionId;
  }

  public get streamUrl() {
    return `${this.baseUrl}/camera/stream`;
  }

  public get snapshotUrl() {
    return `${this.baseUrl}/camera/snapshot`;
  }

  private handleResponse<T>(response: AxiosResponse<T>): ApiResponse<T> {
    if (response.status === 204) {
      return {
        data: {} as T,
        status: response.status,
      };
    }
    return {
      data: response.data,
      status: response.status,
    };
  }

  private handleError(error: AxiosError<ErrorResponse>): ApiResponse {
    if (axios.isCancel(error) || error.code === "ECONNABORTED") {
      return {
        error: `Network request timed out after ${this.timeout}ms`,
        status: 0,
      };
    }

    if (error.response) {
      const errorData = error.response.data;
      const errorMessage =
        errorData?.message || errorData?.error || "Request failed";
      return {
        error: errorMessage,
        status: error.response.status,
      };
    } else if (error.request) {
      return {
        error: "Network error - No response from robot",
        status: 0,
      };
    } else {
      return {
        error: error.message || "Unknown error",
        status: 0,
      };
    }
  }

  // Generic HTTP methods
  private async get<T = any>(endpoint: string): Promise<ApiResponse<T>> {
    try {
      console.log("GET request to:", endpoint);
      const response = await this.axiosInstance.get<T>(endpoint);
      return this.handleResponse(response);
    } catch (error) {
      return this.handleError(error as AxiosError<ErrorResponse>);
    }
  }

  private async post<T = any>(
    endpoint: string,
    data?: any
  ): Promise<ApiResponse<T>> {
    try {
      console.log("POST request to:", endpoint, "with data:", data);

      // CRITICAL for React Native: Always send data object, even if empty
      // React Native's XMLHttpRequest may convert POST to GET if no body is present
      const requestData = data !== undefined ? data : {};

      const response = await this.axiosInstance({
        method: "post",
        url: endpoint,
        data: requestData,
        headers: {
          "Content-Type": "application/json",
        },
      });

      console.log("POST response:", response.status, response.data);
      return this.handleResponse(response);
    } catch (error) {
      console.error("POST error:", error);
      return this.handleError(error as AxiosError<ErrorResponse>);
    }
  }

  private async put<T = any>(
    endpoint: string,
    data?: any
  ): Promise<ApiResponse<T>> {
    try {
      console.log("PUT request to:", endpoint, "with data:", data);
      const response = await this.axiosInstance.request<T>({
        method: "PUT",
        url: endpoint,
        data: data || {},
      });
      return this.handleResponse(response);
    } catch (error) {
      return this.handleError(error as AxiosError<ErrorResponse>);
    }
  }

  private async delete<T = any>(endpoint: string): Promise<ApiResponse<T>> {
    try {
      console.log("DELETE request to:", endpoint);
      const response = await this.axiosInstance.request<T>({
        method: "DELETE",
        url: endpoint,
      });
      return this.handleResponse(response);
    } catch (error) {
      return this.handleError(error as AxiosError<ErrorResponse>);
    }
  }

  // Public API methods
  public async ping(): Promise<RobotHealth> {
    const response = await this.get<RobotHealth>("/health");
    if (response.error) {
      throw new Error(response.error);
    }
    return response.data!;
  }

  public async fetchHealth(): Promise<RobotHealth> {
    const response = await this.get<RobotHealth>("/health");
    if (response.error) {
      throw new Error(response.error);
    }
    return response.data!;
  }

  public async fetchNetworkInfo(): Promise<RobotNetworkInfo> {
    const response = await this.get<RobotNetworkInfo>("/wifi/status");
    if (response.error) {
      throw new Error(response.error);
    }
    return response.data!;
  }

  public async fetchTelemetry(): Promise<RobotTelemetry> {
    const response = await this.get<RobotTelemetry>("/status");
    if (response.error) {
      throw new Error(response.error);
    }
    return response.data!;
  }

  public async fetchMode(): Promise<RobotModeState> {
    const response = await this.get<RobotModeState>("/mode");
    if (response.error) {
      throw new Error(response.error);
    }
    return response.data!;
  }

  public async connectWifi(
    credentials: WifiCredentials
  ): Promise<{ success: boolean }> {
    const response = await this.post<{ success: boolean }>(
      "/wifi/connect",
      credentials
    );
    if (response.error) {
      throw new Error(response.error);
    }
    return response.data!;
  }

  public async capturePhoto(): Promise<CameraCaptureMetadata> {
    const response = await this.post<CameraCaptureMetadata>("/camera/capture");
    if (response.error) {
      throw new Error(response.error);
    }
    return response.data!;
  }

  public async listWifiNetworks(): Promise<WifiScanResponse> {
    const response = await this.get<WifiScanResponse>("/wifi/networks");
    if (response.error) {
      throw new Error(response.error);
    }
    return response.data!;
  }

  public async fetchWifiStatus(): Promise<RobotNetworkInfo> {
    const response = await this.get<RobotNetworkInfo>("/wifi/status");
    if (response.error) {
      throw new Error(response.error);
    }
    return response.data!;
  }

  public async scanWifiNetworks(): Promise<WifiScanResponse> {
    const response = await this.get<WifiScanResponse>("/wifi/scan");
    if (response.error) {
      throw new Error(response.error);
    }
    return response.data!;
  }

  public async requestClaim(): Promise<ClaimRequestResponse> {
    try {
      console.log("=== REQUEST CLAIM DEBUG START ===");
      console.log("Base URL:", this.baseUrl);

      const url = `${this.baseUrl}/claim/request`;
      console.log("Full URL:", url);

      // Test if the URL is reachable with a simple GET first
      try {
        console.log("Testing GET request to /health...");
        const healthResponse = await fetch(`${this.baseUrl}/health`, {
          method: "GET",
        });
        console.log("Health check status:", healthResponse.status);
      } catch (healthErr) {
        console.error("Health check failed:", healthErr);
      }

      // Now try the POST
      console.log("Attempting POST request...");
      console.log("Method: POST");
      console.log("URL:", url);
      console.log("Body:", JSON.stringify({}));

      const requestOptions = {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        body: JSON.stringify({}),
      };

      console.log("Request options:", JSON.stringify(requestOptions, null, 2));

      const response = await fetch(url, requestOptions);

      console.log("Response received:");
      console.log("  Status:", response.status);
      console.log("  Status Text:", response.statusText);
      console.log(
        "  Headers:",
        JSON.stringify(Object.fromEntries(response.headers.entries()))
      );

      if (!response.ok) {
        const errorText = await response.text();
        console.error("Error response body:", errorText);
        console.log("=== REQUEST CLAIM DEBUG END (ERROR) ===");
        throw new Error(
          `Request failed with status ${response.status}: ${errorText}`
        );
      }

      const data = await response.json();
      console.log("Response data:", data);
      console.log("=== REQUEST CLAIM DEBUG END (SUCCESS) ===");
      return data as ClaimRequestResponse;
    } catch (error) {
      console.error("=== REQUEST CLAIM DEBUG END (EXCEPTION) ===");
      console.error("Exception:", error);
      if (error instanceof Error) {
        throw new Error(`Request failed: ${error.message}`);
      }
      throw error;
    }
  }

  public async confirmClaim(
    pin: string,
    deviceId: string,
    deviceInfo?: {
      name?: string;
      platform?: string;
      app_version?: string;
    }
  ): Promise<ClaimConfirmResponse> {
    const payload: {
      pin: string;
      device_id: string;
      name?: string;
      platform?: string;
      app_version?: string;
    } = {
      pin,
      device_id: deviceId,
    };

    if (deviceInfo) {
      if (deviceInfo.name) payload.name = deviceInfo.name;
      if (deviceInfo.platform) payload.platform = deviceInfo.platform;
      if (deviceInfo.app_version) payload.app_version = deviceInfo.app_version;
    }

    const response = await this.post<ClaimConfirmResponse>("/claim/confirm", payload);
    if (response.error) {
      throw new Error(response.error);
    }
    return response.data!;
  }

  public async move(payload: { linear: number; angular: number }) {
    const response = await this.post("/control/move", payload);
    if (response.error) {
      throw new Error(response.error);
    }
    return response.data!;
  }

  public async stop() {
    const response = await this.post("/control/stop");
    if (response.error) {
      throw new Error(response.error);
    }
    return response.data!;
  }

  public async moveHead(payload: { pan: number; tilt: number }) {
    const response = await this.post("/control/head", payload);
    if (response.error) {
      throw new Error(response.error);
    }
    return response.data!;
  }

  public async controlLights(payload: { pwmA: number; pwmB: number }) {
    const response = await this.post("/control/lights", payload);
    if (response.error) {
      throw new Error(response.error);
    }
    return response.data!;
  }

  public async nod(
    payload: {
      times?: number;
      center_tilt?: number;
      delta?: number;
      pan?: number;
      delay?: number;
    } = {}
  ) {
    const response = await this.post("/control/nod", payload);
    if (response.error) {
      throw new Error(response.error);
    }
    return response.data!;
  }

  // Utility methods
  public setHeader(key: string, value: string) {
    this.axiosInstance.defaults.headers.common[key] = value;
  }

  public removeHeader(key: string) {
    delete this.axiosInstance.defaults.headers.common[key];
  }

  public getAxiosInstance(): AxiosInstance {
    return this.axiosInstance;
  }

  // Organized namespace methods (optional, similar to your ApiClient)
  public camera = {
    capture: () => this.capturePhoto(),
    getStreamUrl: () => this.streamUrl,
    getSnapshotUrl: () => this.snapshotUrl,
  };

  public wifi = {
    connect: (credentials: WifiCredentials) => this.connectWifi(credentials),
    listNetworks: () => this.listWifiNetworks(),
    scan: () => this.scanWifiNetworks(),
    getStatus: () => this.fetchWifiStatus(),
  };

  public control = {
    move: (payload: { linear: number; angular: number }) => this.move(payload),
    stop: () => this.stop(),
    moveHead: (payload: { pan: number; tilt: number }) =>
      this.moveHead(payload),
    lights: (payload: { pwmA: number; pwmB: number }) =>
      this.controlLights(payload),
    nod: (payload?: {
      times?: number;
      center_tilt?: number;
      delta?: number;
      pan?: number;
      delay?: number;
    }) => this.nod(payload),
  };
}

export const createRobotApi = (
  baseUrl: string,
  timeout?: number,
  sessionId?: string | null
) => new RobotAPI({ baseUrl, timeout, sessionId });
