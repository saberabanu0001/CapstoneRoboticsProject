declare module "expo-network" {
  export type NetworkStateType =
    | "UNKNOWN"
    | "NONE"
    | "CELLULAR"
    | "WIFI"
    | "OTHER";

  export type NetworkState = {
    type: NetworkStateType;
    isConnected?: boolean;
    isInternetReachable?: boolean | null;
  };

  export function getNetworkStateAsync(): Promise<NetworkState>;
  export function getIpAddressAsync(): Promise<string>;
}
