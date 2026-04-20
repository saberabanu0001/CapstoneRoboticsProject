import AsyncStorage from "@react-native-async-storage/async-storage";

export interface StoredRobot {
  robot_id: string;
  name?: string;
  baseUrl: string;
  device_id: string;
  control_token?: string;
  last_ip?: string;
  last_wifi_ssid?: string;
  last_seen?: string;
  // Optional metadata
  platform?: string;
  app_version?: string;
}

const ROBOTS_STORAGE_KEY = "paired_robots";

/**
 * Gets all stored robots.
 */
export async function getStoredRobots(): Promise<StoredRobot[]> {
  try {
    const data = await AsyncStorage.getItem(ROBOTS_STORAGE_KEY);
    if (!data) {
      return [];
    }
    const robots = JSON.parse(data) as StoredRobot[];
    return robots;
  } catch (error) {
    console.error("Failed to get stored robots", error);
    return [];
  }
}

/**
 * Gets a stored robot by robot_id.
 */
export async function getStoredRobot(robotId: string): Promise<StoredRobot | null> {
  const robots = await getStoredRobots();
  return robots.find((r) => r.robot_id === robotId) ?? null;
}

/**
 * Gets a stored robot by baseUrl or IP.
 */
export async function getStoredRobotByUrl(baseUrl: string): Promise<StoredRobot | null> {
  const robots = await getStoredRobots();
  const urlLower = baseUrl.toLowerCase();
  
  // Try exact match first
  let robot = robots.find((r) => r.baseUrl.toLowerCase() === urlLower);
  if (robot) {
    return robot;
  }

  // Try matching by IP
  const urlIp = extractIpFromUrl(baseUrl);
  if (urlIp) {
    robot = robots.find((r) => {
      const storedIp = r.last_ip || extractIpFromUrl(r.baseUrl);
      return storedIp === urlIp;
    });
    if (robot) {
      return robot;
    }
  }

  return null;
}

/**
 * Saves or updates a robot.
 */
export async function saveRobot(robot: StoredRobot): Promise<void> {
  try {
    const robots = await getStoredRobots();
    const existingIndex = robots.findIndex((r) => r.robot_id === robot.robot_id);

    const updatedRobot: StoredRobot = {
      ...robot,
      last_seen: new Date().toISOString(),
    };

    if (existingIndex >= 0) {
      // Update existing
      robots[existingIndex] = updatedRobot;
    } else {
      // Add new
      robots.push(updatedRobot);
    }

    await AsyncStorage.setItem(ROBOTS_STORAGE_KEY, JSON.stringify(robots));
    console.log("Saved robot:", robot.robot_id);
  } catch (error) {
    console.error("Failed to save robot", error);
    throw error;
  }
}

/**
 * Removes a robot by robot_id.
 */
export async function removeRobot(robotId: string): Promise<void> {
  try {
    const robots = await getStoredRobots();
    const filtered = robots.filter((r) => r.robot_id !== robotId);
    await AsyncStorage.setItem(ROBOTS_STORAGE_KEY, JSON.stringify(filtered));
    console.log("Removed robot:", robotId);
  } catch (error) {
    console.error("Failed to remove robot", error);
    throw error;
  }
}

/**
 * Updates the last_seen timestamp for a robot.
 */
export async function updateRobotLastSeen(robotId: string): Promise<void> {
  try {
    const robots = await getStoredRobots();
    const robot = robots.find((r) => r.robot_id === robotId);
    if (robot) {
      robot.last_seen = new Date().toISOString();
      await AsyncStorage.setItem(ROBOTS_STORAGE_KEY, JSON.stringify(robots));
    }
  } catch (error) {
    console.error("Failed to update robot last seen", error);
  }
}

/**
 * Updates the last_ip for a robot.
 */
export async function updateRobotLastIp(robotId: string, ip: string): Promise<void> {
  try {
    const robots = await getStoredRobots();
    const robot = robots.find((r) => r.robot_id === robotId);
    if (robot) {
      robot.last_ip = ip;
      await AsyncStorage.setItem(ROBOTS_STORAGE_KEY, JSON.stringify(robots));
    }
  } catch (error) {
    console.error("Failed to update robot last IP", error);
  }
}

/**
 * Updates the last_wifi_ssid for a robot.
 */
export async function updateRobotLastWifiSsid(robotId: string, ssid: string): Promise<void> {
  try {
    const robots = await getStoredRobots();
    const robot = robots.find((r) => r.robot_id === robotId);
    if (robot) {
      robot.last_wifi_ssid = ssid;
      await AsyncStorage.setItem(ROBOTS_STORAGE_KEY, JSON.stringify(robots));
    }
  } catch (error) {
    console.error("Failed to update robot last WiFi SSID", error);
  }
}

/**
 * Robot status check result
 */
export interface RobotStatusCheck {
  robot: StoredRobot;
  status: "ready" | "needs_repair" | "offline";
  robotStatus?: {
    robotId?: string;
    name?: string;
    wifi?: {
      connected: boolean;
      ssid?: string;
      ip?: string;
    };
    claimed?: boolean;
    tokenValid?: boolean;
  };
}

/**
 * Extracts IP address from a URL.
 */
function extractIpFromUrl(url: string): string | null {
  try {
    const parsed = new URL(url.startsWith("http") ? url : `http://${url}`);
    const hostname = parsed.hostname;
    
    // Check if it's an IPv4 address
    const ipv4Regex = /^(\d{1,3}\.){3}\d{1,3}$/;
    if (ipv4Regex.test(hostname)) {
      return hostname;
    }
    
    return null;
  } catch (error) {
    return null;
  }
}

