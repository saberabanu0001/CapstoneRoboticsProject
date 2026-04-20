import { createRobotApi } from "./robot-api";
import { getStoredRobots, RobotStatusCheck } from "./robot-storage";

/**
 * Checks the status of a stored robot silently.
 * Returns the status and robot info if available.
 */
export async function checkRobotStatus(
  robot: { robot_id: string; last_ip?: string; control_token?: string; baseUrl?: string }
): Promise<RobotStatusCheck> {
  const baseUrl = robot.baseUrl || (robot.last_ip ? `http://${robot.last_ip}:8000` : null);
  
  if (!baseUrl) {
    return {
      robot: robot as any,
      status: "offline",
    };
  }

  try {
    const api = createRobotApi(baseUrl, 3000);
    
    // Try to fetch status
    const statusResponse = await api.fetchTelemetry();
    
    // Check if we got a valid response
    // The API should return robotId, name, wifi, claimed, tokenValid
    const robotStatus = statusResponse as any;
    
    // If tokenValid is false or claimed is false, needs re-pair
    if (robotStatus.tokenValid === false || robotStatus.claimed === false) {
      return {
        robot: robot as any,
        status: "needs_repair",
        robotStatus,
      };
    }
    
    // If we got here and have valid data, robot is ready
    return {
      robot: robot as any,
      status: "ready",
      robotStatus,
    };
  } catch (error) {
    // Network error or robot not reachable
    console.log(`Robot ${robot.robot_id} status check failed:`, error);
    return {
      robot: robot as any,
      status: "offline",
    };
  }
}

/**
 * Checks status of all stored robots.
 */
export async function checkAllRobotsStatus(): Promise<RobotStatusCheck[]> {
  const robots = await getStoredRobots();
  const checks = await Promise.all(robots.map((robot) => checkRobotStatus(robot)));
  return checks;
}

