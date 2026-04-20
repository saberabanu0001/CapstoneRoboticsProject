/**
 * Cloud AI API - Connects to PC server for AI processing
 * 
 * This is separate from robot-api.ts which connects to the Pi.
 * 
 * Architecture:
 *   Phone App → Pi (robot-api.ts): Camera, rover control, lights, WiFi
 *   Phone App → PC (cloud-api.ts): Chat, vision, STT, TTS
 */

import axios, { AxiosInstance } from "axios";
import { CLOUD_API_BASE_URL } from "@/constants/env";

// Default Cloud PC IP (Tailscale) - FastAPI runs on port 8000
// Falls back to environment variable if set, otherwise uses hardcoded IP
export const DEFAULT_CLOUD_URL = CLOUD_API_BASE_URL || "http://100.121.110.125:8000";

export interface ChatRequest {
  message: string;
  max_tokens?: number;
  temperature?: number;
}

export interface ChatResponse {
  response: string;
  movement?: {
    direction: string;
    distance: number;
    speed: string;
  };
}

export interface VisionRequest {
  question: string;
  image_base64: string;
  max_tokens?: number;
}

export interface VisionResponse {
  response: string;
  movement?: {
    direction: string;
    distance: number;
    speed: string;
  };
}

export interface STTResponse {
  text: string | null;
  success: boolean;
}

export interface CloudHealth {
  ok: boolean;
  assistant_loaded?: boolean;
  speech_loaded?: boolean;
  meeting_service_available?: boolean;
  // Robot fields (when cloud runs on robot)
  name?: string;
  serial?: string;
  claimed?: boolean;
  mode?: string;
  version?: string;
  battery?: number;
}

export interface MeetingSummary {
  id: string;
  title: string;
  type: 'meeting' | 'lecture' | 'conversation' | 'note';
  content: string;
  transcript?: string;
  date: string; // ISO timestamp
  duration?: number;
  audio_filename?: string;
}

export interface MeetingSummaryListResponse {
  summaries: MeetingSummary[];
  count: number;
}

export interface CloudApiOptions {
  baseUrl?: string;
  timeout?: number;
}

export class CloudAPI {
  private baseUrl: string;
  private axiosInstance: AxiosInstance;
  private timeout: number;

  constructor(options: CloudApiOptions = {}) {
    this.baseUrl = (options.baseUrl || DEFAULT_CLOUD_URL).replace(/\/$/, "");
    this.timeout = options.timeout ?? 30000; // Longer timeout for AI processing

    this.axiosInstance = axios.create({
      baseURL: this.baseUrl,
      timeout: this.timeout,
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
    });
  }

  public updateBaseUrl(baseUrl: string) {
    this.baseUrl = baseUrl.replace(/\/$/, "");
    this.axiosInstance.defaults.baseURL = this.baseUrl;
  }

  public getBaseUrl(): string {
    return this.baseUrl;
  }

  /**
   * Check cloud server health
   */
  public async health(): Promise<CloudHealth> {
    const response = await this.axiosInstance.get<CloudHealth>("/health");
    return response.data;
  }

  /**
   * Chat with AI (text only)
   */
  public async chat(request: ChatRequest): Promise<ChatResponse> {
    const response = await this.axiosInstance.post<ChatResponse>("/chat", {
      message: request.message,
      max_tokens: request.max_tokens ?? 150,
      temperature: request.temperature ?? 0.7,
    });
    return response.data;
  }

  /**
   * Ask AI about an image
   */
  public async vision(request: VisionRequest): Promise<VisionResponse> {
    const response = await this.axiosInstance.post<VisionResponse>("/vision", {
      question: request.question,
      image_base64: request.image_base64,
      max_tokens: request.max_tokens ?? 200,
    });
    return response.data;
  }

  /**
   * Convert speech to text
   * @param audioBlob Audio data as Blob or File
   */
  public async speechToText(audioBlob: Blob): Promise<STTResponse> {
    const formData = new FormData();
    formData.append("audio", audioBlob, "audio.wav");

    const response = await this.axiosInstance.post<STTResponse>("/stt", formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    });
    return response.data;
  }

  /**
   * Convert text to speech
   * @returns Audio data as ArrayBuffer (WAV format)
   */
  public async textToSpeech(text: string): Promise<ArrayBuffer> {
    const response = await this.axiosInstance.post("/tts", { text }, {
      responseType: "arraybuffer",
    });
    return response.data;
  }

  /**
   * Get WebSocket URL for real-time voice interaction
   */
  public getVoiceWebSocketUrl(): string {
    const wsBase = this.baseUrl.replace(/^http/, "ws");
    return `${wsBase}/voice`;
  }

  /**
   * Get all meeting summaries
   */
  public async getMeetings(): Promise<MeetingSummaryListResponse> {
    const response = await this.axiosInstance.get<MeetingSummaryListResponse>("/meetings");
    return response.data;
  }

  /**
   * Get a specific meeting by ID
   */
  public async getMeeting(meetingId: string): Promise<MeetingSummary> {
    const response = await this.axiosInstance.get<MeetingSummary>(`/meetings/${meetingId}`);
    return response.data;
  }

  /**
   * Upload meeting audio for transcription and summarization
   */
  public async uploadMeeting(
    audioBlob: Blob,
    title?: string,
    meetingType: 'meeting' | 'lecture' | 'conversation' | 'note' = 'meeting'
  ): Promise<{ success: boolean; meeting_id: string; message: string }> {
    const formData = new FormData();
    formData.append("audio", audioBlob, "meeting.wav");
    if (title) {
      formData.append("title", title);
    }
    formData.append("meeting_type", meetingType);

    const response = await this.axiosInstance.post("/meetings/upload", formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
      timeout: 120000, // 2 minutes for transcription/summarization
    });
    return response.data;
  }

  /**
   * Delete a meeting by ID
   */
  public async deleteMeeting(meetingId: string): Promise<{ status: string; message: string }> {
    const response = await this.axiosInstance.delete(`/meetings/${meetingId}`);
    return response.data;
  }
}

/**
 * Create a CloudAPI instance
 */
export const createCloudApi = (baseUrl?: string, timeout?: number) =>
  new CloudAPI({ baseUrl, timeout });

/**
 * Default cloud API instance (uses Tailscale IP)
 */
export const cloudApi = new CloudAPI();
