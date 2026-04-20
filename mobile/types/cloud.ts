export interface CloudUser {
  id: string;
  email: string;
  name?: string | null;
  createdAt?: string;
}

export interface CloudSession {
  token: string;
  user: CloudUser;
}

export interface CloudRobot {
  id: string;
  serial: string;
  name?: string | null;
  ownerUserId?: string | null;
  claimedAt?: string | null;
  lastSeenAt?: string | null;
  lastSeenMeta?: Record<string, unknown> | null;
  controlTokenHint?: string | null;
}

export interface NearbyRobotSummary {
  serial: string;
  name?: string | null;
  ip?: string | null;
  ownerUserId?: string | null;
  lastSeenAt?: string | null;
  lastSeenMeta?: Record<string, unknown> | null;
}

export interface ClaimRobotResponse {
  robot: CloudRobot;
  controlToken?: string | null;
  robotBaseUrl?: string | null;
}
