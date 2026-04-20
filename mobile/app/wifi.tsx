import { useRouter } from "expo-router";
import React, { useCallback, useEffect, useState } from "react";
import {
     ActivityIndicator,
     Alert,
     Pressable,
     RefreshControl,
     ScrollView,
     StyleSheet,
     View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { ThemedText } from "@/components/themed-text";
import { ThemedView } from "@/components/themed-view";
import { IconSymbol } from "@/components/ui/icon-symbol";
import { useRobot } from "@/context/robot-provider";

export default function WifiStatusScreen() {
     const router = useRouter();
     const { api, status, refreshStatus } = useRobot();
     const statusRef = React.useRef(status);

     // Keep status ref updated without causing re-renders
     React.useEffect(() => {
          statusRef.current = status;
     }, [status]);

     const [wifiStatus, setWifiStatus] = useState<{
          ssid?: string;
          ip?: string;
          connected?: boolean;
     } | null>(null);
     const [availableNetworks, setAvailableNetworks] = useState<
          ({ ssid: string; signal_strength?: number; security?: string; frequency?: number } | string)[]
     >([]);
     const [showNetworks, setShowNetworks] = useState(false);
     const [isLoading, setIsLoading] = useState(true);
     const [isRefreshing, setIsRefreshing] = useState(false);
     const [isScanning, setIsScanning] = useState(false);

     const loadWifiStatus = useCallback(async () => {
          try {
               const wifiStatusData = await api.fetchWifiStatus();
               setWifiStatus({
                    ssid: wifiStatusData.network_name || wifiStatusData.ssid || wifiStatusData.wifiSsid,
                    ip: wifiStatusData.ip,
                    connected: wifiStatusData.connected ?? Boolean(
                         wifiStatusData.network_name || wifiStatusData.ssid || wifiStatusData.wifiSsid
                    ),
               });
          } catch (error) {
               console.warn("Failed to fetch WiFi status, using robot status:", error);
               // Fallback to robot status if WiFi status endpoint fails
               const currentStatus = statusRef.current;
               if (currentStatus) {
                    setWifiStatus({
                         ssid: currentStatus.network?.ssid || currentStatus.network?.wifiSsid,
                         ip: currentStatus.network?.ip,
                         connected: Boolean(
                              currentStatus.network?.ssid || currentStatus.network?.wifiSsid
                         ),
                    });
               }
          }
     }, [api]);

     const scanNetworks = useCallback(async () => {
          try {
               setIsScanning(true);
               const scanResult = await api.scanWifiNetworks();
               // Handle both object and string formats
               const networks = (scanResult.networks || []).map((network) => {
                    if (typeof network === "string") {
                         return network;
                    }
                    return network;
               });
               setAvailableNetworks(networks);
          } catch (error) {
               console.error("Failed to scan WiFi networks:", error);
               // Fallback to listWifiNetworks if scan endpoint fails
               try {
                    const networksResult = await api.listWifiNetworks();
                    // Handle both object and string formats
                    const networks = (networksResult.networks || []).map((network) => {
                         if (typeof network === "string") {
                              return network;
                         }
                         return network;
                    });
                    setAvailableNetworks(networks);
               } catch (fallbackError) {
                    console.error("Failed to list WiFi networks:", fallbackError);
                    Alert.alert(
                         "Error",
                         "Failed to load available networks. Please try again."
                    );
               }
          } finally {
               setIsScanning(false);
          }
     }, [api]);

     const loadData = useCallback(async () => {
          setIsLoading(true);
          try {
               // Only load WiFi status on mount, don't call refreshStatus (robot-provider handles polling)
               await loadWifiStatus();
          } catch (error) {
               console.error("Failed to load WiFi data:", error);
          } finally {
               setIsLoading(false);
          }
     }, [loadWifiStatus]);

     const handleRefresh = useCallback(async () => {
          setIsRefreshing(true);
          try {
               // Only refresh WiFi status and scan networks, don't call refreshStatus (robot-provider handles polling)
               await Promise.all([loadWifiStatus(), scanNetworks()]);
          } catch (error) {
               console.error("Failed to refresh WiFi data:", error);
          } finally {
               setIsRefreshing(false);
          }
     }, [loadWifiStatus, scanNetworks]);

     // Load WiFi status once on mount
     useEffect(() => {
          loadData();
          // eslint-disable-next-line react-hooks/exhaustive-deps
     }, []); // Only run once on mount

     const currentSsid = wifiStatus?.ssid || status?.network?.ssid || status?.network?.wifiSsid;
     const currentIp = wifiStatus?.ip || status?.network?.ip;
     const isConnected = wifiStatus?.connected ?? Boolean(currentSsid);
     const handleConnectToRobot = useCallback(async () => {
          try {
               await refreshStatus();
               router.push("/(tabs)/home");
          } catch (error) {
               Alert.alert(
                    "Connection Error",
                    error instanceof Error ? error.message : "Failed to connect to robot"
               );
          }
     }, [refreshStatus, router]);

     const handleChangeWifi = useCallback(async () => {
          // Show networks section and scan for networks when button is pressed
          setShowNetworks(true);
          await scanNetworks();
     }, [scanNetworks]);

     if (isLoading) {
          return (
               <SafeAreaView style={styles.safeArea} edges={["top"]}>
                    <ThemedView style={styles.container}>
                         <View style={styles.loadingContainer}>
                              <ActivityIndicator size="large" color="#1DD1A1" />
                              <ThemedText style={styles.loadingText}>Loading WiFi status...</ThemedText>
                         </View>
                    </ThemedView>
               </SafeAreaView>
          );
     }

     return (
          <SafeAreaView style={styles.safeArea} edges={["top", "bottom"]}>
               <ThemedView style={styles.container}>
                    <ScrollView
                         style={styles.scrollView}
                         contentContainerStyle={styles.scrollContent}
                         refreshControl={
                              <RefreshControl
                                   refreshing={isRefreshing}
                                   onRefresh={handleRefresh}
                                   tintColor="#1DD1A1"
                              />
                         }
                    >
                         <ThemedText type="title" style={styles.title}>
                              Robot WiFi Status
                         </ThemedText>

                         <View style={styles.networks}>
                              {/* Current WiFi Connection Status */}
                              <ThemedView style={styles.statusCard}>
                                   <View style={styles.statusRow}>
                                        <ThemedText style={styles.statusLabel}>WiFi Connection:</ThemedText>
                                        <View style={styles.statusValueRow}>
                                             <View
                                                  style={[
                                                       styles.statusIndicator,
                                                       { backgroundColor: isConnected ? "#1DD1A1" : "#67686C" },
                                                  ]}
                                             />
                                             <ThemedText style={styles.statusValue}>
                                                  {isConnected ? "Connected" : "Disconnected"}
                                             </ThemedText>
                                        </View>
                                   </View>
                                   <View style={styles.statusRow}>
                                        <ThemedText style={styles.statusLabel}>Network Name:</ThemedText>
                                        <ThemedText style={styles.statusValue}>
                                             {currentSsid || "Not connected"}
                                        </ThemedText>
                                   </View>
                                   <View style={styles.statusRow}>
                                        <ThemedText style={styles.statusLabel}>IP Address:</ThemedText>
                                        <ThemedText style={styles.statusValue}>
                                             {currentIp || "Unavailable"}
                                        </ThemedText>
                                   </View>
                              </ThemedView>

                              {/* Available Networks Section - Only show when Change Robot WiFi button is pressed */}
                              {showNetworks && (
                                   <View style={styles.networksSection}>
                                        <View style={styles.sectionHeader}>
                                             <ThemedText style={styles.sectionTitle}>Available networks</ThemedText>
                                             <Pressable
                                                  onPress={scanNetworks}
                                                  disabled={isScanning}
                                                  style={({ pressed }) => [
                                                       styles.refreshButton,
                                                       pressed && styles.refreshButtonPressed,
                                                       isScanning && styles.refreshButtonDisabled,
                                                  ]}
                                             >
                                                  {isScanning ? (
                                                       <ActivityIndicator size="small" color="#1DD1A1" />
                                                  ) : (
                                                       <IconSymbol name="arrow.clockwise" size={18} color="#1DD1A1" />
                                                  )}
                                             </Pressable>
                                        </View>

                                        {availableNetworks.length > 0 ? (
                                             <ThemedView style={styles.networksList}>
                                                  {availableNetworks.map((network, index) => {
                                                       // Extract SSID from network (could be string or object)
                                                       const networkSsid = typeof network === "string" ? network : network.ssid;
                                                       const isCurrentNetwork = networkSsid === currentSsid;
                                                       return (
                                                            <View
                                                                 key={`${networkSsid}-${index}`}
                                                                 style={[
                                                                      styles.networkItem,
                                                                      index < availableNetworks.length - 1 && styles.networkItemBorder,
                                                                 ]}
                                                            >
                                                                 <View style={styles.networkItemContent}>
                                                                      {isCurrentNetwork && (
                                                                           <View
                                                                                style={[
                                                                                     styles.statusIndicator,
                                                                                     { backgroundColor: "#1DD1A1", marginRight: 8 },
                                                                                ]}
                                                                           />
                                                                      )}
                                                                      <ThemedText
                                                                           style={[
                                                                                styles.networkName,
                                                                                isCurrentNetwork && styles.networkNameActive,
                                                                           ]}
                                                                      >
                                                                           {networkSsid}
                                                                      </ThemedText>
                                                                 </View>
                                                            </View>
                                                       );
                                                  })}
                                             </ThemedView>
                                        ) : (
                                             <ThemedView style={styles.emptyState}>
                                                  <ThemedText style={styles.emptyStateText}>
                                                       {isScanning ? "Scanning for networks..." : "No networks found. Tap refresh to scan."}
                                                  </ThemedText>
                                             </ThemedView>
                                        )}
                                   </View>
                              )}
                         </View>
                    </ScrollView>

                    {/* Action Buttons - Fixed at bottom */}
                    <View style={styles.buttonsContainer}>
                         <Pressable
                              onPress={handleConnectToRobot}
                              style={({ pressed }) => [
                                   styles.actionButton,
                                   styles.primaryButton,
                                   pressed && styles.buttonPressed,
                              ]}
                         >
                              <ThemedText style={styles.primaryButtonText}>Connect to Robot</ThemedText>
                         </Pressable>

                         <Pressable
                              onPress={handleChangeWifi}
                              style={({ pressed }) => [
                                   styles.actionButton,
                                   styles.secondaryButton,
                                   pressed && styles.buttonPressed,
                              ]}
                         >
                              <ThemedText style={styles.secondaryButtonText}>Change Robot WiFi</ThemedText>
                         </Pressable>
                    </View>
               </ThemedView>
          </SafeAreaView>
     );
}

const styles = StyleSheet.create({
     safeArea: {
          flex: 1,
          backgroundColor: "#161616",
     },
     container: {
          flex: 1,
          backgroundColor: "#161616",
     },
     networks: {
          gap: 12,
     },
     scrollView: {
          flex: 1,
     },
     scrollContent: {
          padding: 20,
          paddingBottom: 20,
          gap: 24,
     },
     loadingContainer: {
          flex: 1,
          justifyContent: "center",
          alignItems: "center",
          gap: 16,
     },
     loadingText: {
          color: "#67686C",
          fontSize: 16,
     },
     title: {
          color: "#F9FAFB",
          fontSize: 28,
          fontFamily: "JetBrainsMono_600SemiBold",
          marginBottom: 8,
     },
     statusCard: {
          backgroundColor: "#1C1C1C",
          padding: 16,
          gap: 16,
     },
     statusRow: {
          flexDirection: "row",
          justifyContent: "space-between",
          alignItems: "center",
     },
     statusLabel: {
          color: "#67686C",
          fontSize: 16,
     },
     statusValue: {
          color: "#F9FAFB",
          fontSize: 16,
          fontFamily: "JetBrainsMono_600SemiBold",
     },
     statusValueRow: {
          flexDirection: "row",
          alignItems: "center",
          gap: 8,
     },
     statusIndicator: {
          width: 10,
          height: 10,
     },
     networksSection: {
          gap: 12,
     },
     sectionHeader: {
          flexDirection: "row",
          justifyContent: "space-between",
          alignItems: "center",
     },
     sectionTitle: {
          color: "#F9FAFB",
          fontSize: 18,
          fontFamily: "JetBrainsMono_600SemiBold",
     },
     refreshButton: {
          padding: 8,
     },
     refreshButtonPressed: {
          opacity: 0.7,
     },
     refreshButtonDisabled: {
          opacity: 0.5,
     },
     networksList: {
          backgroundColor: "#1C1C1C",
          overflow: "hidden",
     },
     networkItem: {
          padding: 16,
     },
     networkItemBorder: {
          borderBottomWidth: 1,
          borderBottomColor: "#202020",
     },
     networkItemContent: {
          flexDirection: "row",
          alignItems: "center",
     },
     networkName: {
          color: "#E5E7EB",
          fontSize: 16,
     },
     networkNameActive: {
          color: "#1DD1A1",
          fontFamily: "JetBrainsMono_600SemiBold",
     },
     emptyState: {
          backgroundColor: "#1C1C1C",
          padding: 24,
          alignItems: "center",
     },
     emptyStateText: {
          color: "#67686C",
          fontSize: 14,
          fontStyle: "italic",
     },
     buttonsContainer: {
          gap: 12,
          padding: 20,
          paddingTop: 12,
          backgroundColor: "#161616",
          borderTopWidth: 1,
          borderTopColor: "#1C1C1C",
     },
     actionButton: {
          paddingVertical: 16,
          paddingHorizontal: 24,
          alignItems: "center",
          justifyContent: "center",
     },
     primaryButton: {
          backgroundColor: "#1C1C1C",
     },
     secondaryButton: {
          backgroundColor: "#1C1C1C",
          borderWidth: 1,
          borderColor: "#202020",
     },
     buttonPressed: {
          opacity: 0.8,
     },
     primaryButtonText: {
          color: "#F9FAFB",
          fontSize: 16,
          fontFamily: "JetBrainsMono_600SemiBold",
     },
     secondaryButtonText: {
          color: "#E5E7EB",
          fontSize: 16,
          fontFamily: "JetBrainsMono_600SemiBold",
     },
});

