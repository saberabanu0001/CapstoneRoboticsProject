import React, { useState, useEffect } from 'react';
import { ScrollView, StyleSheet, View, RefreshControl, ActivityIndicator, TouchableOpacity, Alert, TextInput, Modal } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import Animated, { FadeInDown } from 'react-native-reanimated';
import * as DocumentPicker from 'expo-document-picker';

import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { IconSymbol } from '@/components/ui/icon-symbol';
import { cloudApi, MeetingSummary } from '@/services/cloud-api';

interface Summary {
  id: string;
  title: string;
  type: 'meeting' | 'lecture' | 'conversation' | 'note';
  content: string;
  date: Date;
  icon: string;
}

// Map meeting type to icon
const getIconForType = (type: string): string => {
  switch (type) {
    case 'meeting':
      return 'person.2.fill';
    case 'lecture':
      return 'book.fill';
    case 'conversation':
      return 'message.fill';
    case 'note':
      return 'note.text';
    default:
      return 'doc.text.fill';
  }
};

export default function SummariesScreen() {
  const [summaries, setSummaries] = useState<Summary[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [uploadTitle, setUploadTitle] = useState('');
  const [uploadType, setUploadType] = useState<'meeting' | 'lecture' | 'conversation' | 'note'>('meeting');
  const [selectedFile, setSelectedFile] = useState<DocumentPicker.DocumentPickerAsset | null>(null);

  const fetchMeetings = async (isRefresh: boolean = false) => {
    try {
      if (isRefresh) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }
      setError(null);

      const response = await cloudApi.getMeetings();
      
      // Convert API response to Summary format
      const convertedSummaries: Summary[] = response.summaries.map((meeting: MeetingSummary) => ({
        id: meeting.id,
        title: meeting.title,
        type: meeting.type,
        content: meeting.content,
        date: new Date(meeting.date),
        icon: getIconForType(meeting.type),
      }));

      setSummaries(convertedSummaries);
    } catch (err: any) {
      console.error('Failed to fetch meetings:', err);
      
      // Provide more helpful error messages
      let errorMessage = 'Failed to load meetings. Pull to refresh.';
      if (err?.code === 'ERR_NETWORK' || err?.message?.includes('Network Error')) {
        errorMessage = 'Cannot reach cloud server. Check your network connection and ensure the cloud server is running.';
      } else if (err?.response?.status === 503) {
        errorMessage = 'Meeting service not available on cloud server. It may need to be enabled or dependencies installed.';
      } else if (err?.response?.status === 404) {
        errorMessage = 'Meetings endpoint not found. The cloud server may need to be updated.';
      } else if (err?.response?.status >= 500) {
        errorMessage = 'Cloud server error. Please try again later.';
      }
      
      setError(errorMessage);
      
      // Fallback to empty array on error
      setSummaries([]);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchMeetings();
  }, []);

  const onRefresh = () => {
    fetchMeetings(true);
  };

  const pickAudioFile = async () => {
    try {
      const result = await DocumentPicker.getDocumentAsync({
        type: ['audio/*'],
        copyToCacheDirectory: true,
      });

      if (!result.canceled && result.assets && result.assets.length > 0) {
        setSelectedFile(result.assets[0]);
        setShowUploadModal(true);
      }
    } catch (err) {
      console.error('Error picking file:', err);
      Alert.alert('Error', 'Failed to pick audio file');
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      Alert.alert('Error', 'Please select an audio file');
      return;
    }

    setUploading(true);
    
    try {
      // In React Native, we need to create a proper file object for FormData
      // The URI from DocumentPicker is a local file path
      const formData = new FormData();
      
      // @ts-ignore - React Native FormData accepts URI
      formData.append('audio', {
        uri: selectedFile.uri,
        type: selectedFile.mimeType || 'audio/wav',
        name: selectedFile.name || 'recording.wav',
      });
      
      if (uploadTitle) {
        formData.append('title', uploadTitle);
      }
      formData.append('meeting_type', uploadType);

      // Upload directly using axios with the FormData
      const baseUrl = cloudApi.getBaseUrl();
      const response = await fetch(`${baseUrl}/meetings/upload`, {
        method: 'POST',
        body: formData,
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
        throw new Error(errorData.detail || `Upload failed with status ${response.status}`);
      }

      const result = await response.json();

      Alert.alert('Success', 'Meeting uploaded and processed successfully!');
      
      // Reset form
      setShowUploadModal(false);
      setSelectedFile(null);
      setUploadTitle('');
      setUploadType('meeting');
      
      // Refresh meetings
      await fetchMeetings(true);
    } catch (err: any) {
      console.error('Upload error:', err);
      const errorMessage = err?.message || 'Failed to upload meeting. Please try again.';
      Alert.alert('Error', errorMessage);
    } finally {
      setUploading(false);
    }
  };

  return (
    <SafeAreaView style={styles.safeArea} edges={['top']}>
      <ScrollView 
        contentContainerStyle={styles.scroll}
        showsVerticalScrollIndicator={false}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={onRefresh}
            tintColor="#1DD1A1"
            colors={['#1DD1A1']}
          />
        }
      >
        <ThemedView style={styles.container}>
          <Animated.View entering={FadeInDown.duration(400)}>
            <View style={styles.header}>
              <View style={styles.headerText}>
                <ThemedText type="title">Summaries</ThemedText>
                <ThemedText style={styles.description}>
                  Meeting notes, lecture summaries, and conversation logs
                </ThemedText>
              </View>
              <TouchableOpacity
                style={styles.uploadButton}
                onPress={pickAudioFile}
                disabled={uploading}
              >
                <IconSymbol name="arrow.up.circle.fill" size={24} color="#1DD1A1" />
              </TouchableOpacity>
            </View>
          </Animated.View>

          {/* Upload Modal */}
          <Modal
            visible={showUploadModal}
            transparent
            animationType="slide"
            onRequestClose={() => !uploading && setShowUploadModal(false)}
          >
            <View style={styles.modalOverlay}>
              <ThemedView style={styles.modalContent}>
                <ThemedText style={styles.modalTitle}>Upload Meeting</ThemedText>
                
                <View style={styles.modalSection}>
                  <ThemedText style={styles.modalLabel}>File</ThemedText>
                  <ThemedText style={styles.fileName}>
                    {selectedFile?.name || 'No file selected'}
                  </ThemedText>
                </View>

                <View style={styles.modalSection}>
                  <ThemedText style={styles.modalLabel}>Title (optional)</ThemedText>
                  <TextInput
                    style={styles.input}
                    value={uploadTitle}
                    onChangeText={setUploadTitle}
                    placeholder="e.g., Team Standup"
                    placeholderTextColor="#67686C"
                  />
                </View>

                <View style={styles.modalSection}>
                  <ThemedText style={styles.modalLabel}>Type</ThemedText>
                  <View style={styles.typeSelector}>
                    {(['meeting', 'lecture', 'conversation', 'note'] as const).map((type) => (
                      <TouchableOpacity
                        key={type}
                        style={[
                          styles.typeButton,
                          uploadType === type && styles.typeButtonActive,
                        ]}
                        onPress={() => setUploadType(type)}
                      >
                        <ThemedText
                          style={[
                            styles.typeButtonText,
                            uploadType === type && styles.typeButtonTextActive,
                          ]}
                        >
                          {type.charAt(0).toUpperCase() + type.slice(1)}
                        </ThemedText>
                      </TouchableOpacity>
                    ))}
                  </View>
                </View>

                <View style={styles.modalButtons}>
                  <TouchableOpacity
                    style={[styles.modalButton, styles.cancelButton]}
                    onPress={() => setShowUploadModal(false)}
                    disabled={uploading}
                  >
                    <ThemedText style={styles.cancelButtonText}>Cancel</ThemedText>
                  </TouchableOpacity>
                  
                  <TouchableOpacity
                    style={[styles.modalButton, styles.uploadButtonModal]}
                    onPress={handleUpload}
                    disabled={uploading}
                  >
                    {uploading ? (
                      <ActivityIndicator size="small" color="#FFF" />
                    ) : (
                      <ThemedText style={styles.uploadButtonText}>
                        Upload
                      </ThemedText>
                    )}
                  </TouchableOpacity>
                </View>
              </ThemedView>
            </View>
          </Modal>

          {/* Loading state */}
          {loading && (
            <View style={styles.centerContainer}>
              <ActivityIndicator size="large" color="#1DD1A1" />
              <ThemedText style={styles.loadingText}>Loading meetings...</ThemedText>
            </View>
          )}

          {/* Error state */}
          {error && !loading && (
            <View style={styles.centerContainer}>
              <ThemedText style={styles.errorText}>{error}</ThemedText>
            </View>
          )}

          {/* Empty state */}
          {!loading && !error && summaries.length === 0 && (
            <View style={styles.centerContainer}>
              <ThemedText style={styles.emptyIcon}>📝</ThemedText>
              <ThemedText style={styles.emptyText}>No meetings yet</ThemedText>
              <ThemedText style={styles.emptySubtext}>
                Start recording meetings with your robot
              </ThemedText>
            </View>
          )}

          {/* Summaries */}
          {!loading && summaries.length > 0 && (
            <Animated.View 
              entering={FadeInDown.delay(100).duration(400)}
              style={styles.section}
            >
              <ThemedText style={styles.sectionTitle}>
                SUMMARIES ({summaries.length})
              </ThemedText>
              <View style={styles.summariesList}>
                {summaries.map((summary, index) => (
                  <Animated.View 
                    key={summary.id}
                    entering={FadeInDown.delay(150 + index * 50).duration(300)}
                  >
                    <ThemedView style={styles.summaryCard}>
                      <View style={styles.summaryHeader}>
                        <View style={styles.summaryIconContainer}>
                          <IconSymbol name={summary.icon as any} size={20} color="#1DD1A1" />
                        </View>
                        <View style={styles.summaryTitleContainer}>
                          <ThemedText style={styles.summaryTitle}>{summary.title}</ThemedText>
                          <ThemedText style={styles.summaryDate}>
                            {summary.date.toLocaleDateString('en-US', { 
                              month: 'short', 
                              day: 'numeric',
                              year: 'numeric'
                            })}
                          </ThemedText>
                        </View>
                      </View>
                      <ThemedText style={styles.summaryContent}>{summary.content}</ThemedText>
                    </ThemedView>
                  </Animated.View>
                ))}
              </View>
            </Animated.View>
          )}
        </ThemedView>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: '#0F0F0F',
  },
  scroll: {
    flexGrow: 1,
    paddingBottom: 40,
  },
  container: {
    flex: 1,
    padding: 20,
    gap: 24,
    backgroundColor: '#0F0F0F',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
    gap: 12,
  },
  headerText: {
    flex: 1,
  },
  description: {
    color: '#9CA3AF',
    marginTop: 6,
    fontSize: 14,
  },
  uploadButton: {
    width: 44,
    height: 44,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: 'rgba(29, 209, 161, 0.15)',
    borderRadius: 22,
    marginTop: 4,
  },
  section: {
    gap: 12,
  },
  sectionTitle: {
    fontSize: 12,
    fontFamily: 'JetBrainsMono_600SemiBold',
    color: '#67686C',
    textTransform: 'uppercase',
    letterSpacing: 1.2,
  },
  summariesList: {
    gap: 12,
  },
  summaryCard: {
    padding: 16,
    backgroundColor: 'rgba(26, 26, 26, 0.7)',
    borderWidth: 1,
    borderColor: 'rgba(37, 37, 37, 0.6)',
    borderRadius: 12,
    gap: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.2,
    shadowRadius: 4,
    elevation: 2,
  },
  summaryHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  summaryIconContainer: {
    width: 40,
    height: 40,
    borderRadius: 10,
    backgroundColor: 'rgba(29, 209, 161, 0.15)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  summaryTitleContainer: {
    flex: 1,
  },
  summaryTitle: {
    fontSize: 15,
    fontFamily: 'JetBrainsMono_600SemiBold',
    color: '#E5E7EB',
    marginBottom: 2,
  },
  summaryDate: {
    fontSize: 12,
    color: '#67686C',
  },
  summaryContent: {
    fontSize: 14,
    color: '#9CA3AF',
    lineHeight: 20,
  },
  centerContainer: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 60,
    gap: 12,
  },
  loadingText: {
    fontSize: 14,
    color: '#9CA3AF',
    marginTop: 8,
  },
  errorText: {
    fontSize: 14,
    color: '#EF4444',
    textAlign: 'center',
  },
  emptyIcon: {
    fontSize: 48,
    marginBottom: 8,
  },
  emptyText: {
    fontSize: 16,
    fontFamily: 'JetBrainsMono_600SemiBold',
    color: '#9CA3AF',
    marginTop: 4,
  },
  emptySubtext: {
    fontSize: 13,
    color: '#67686C',
    textAlign: 'center',
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.8)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  modalContent: {
    width: '100%',
    maxWidth: 400,
    backgroundColor: '#1A1A1A',
    borderRadius: 16,
    padding: 24,
    gap: 20,
    borderWidth: 1,
    borderColor: 'rgba(37, 37, 37, 0.6)',
  },
  modalTitle: {
    fontSize: 20,
    fontFamily: 'JetBrainsMono_600SemiBold',
    color: '#E5E7EB',
  },
  modalSection: {
    gap: 8,
  },
  modalLabel: {
    fontSize: 13,
    fontFamily: 'JetBrainsMono_600SemiBold',
    color: '#9CA3AF',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  fileName: {
    fontSize: 14,
    color: '#E5E7EB',
    padding: 12,
    backgroundColor: 'rgba(0, 0, 0, 0.3)',
    borderRadius: 8,
    borderWidth: 1,
    borderColor: 'rgba(37, 37, 37, 0.6)',
  },
  input: {
    fontSize: 14,
    color: '#E5E7EB',
    padding: 12,
    backgroundColor: 'rgba(0, 0, 0, 0.3)',
    borderRadius: 8,
    borderWidth: 1,
    borderColor: 'rgba(37, 37, 37, 0.6)',
  },
  typeSelector: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  typeButton: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 8,
    backgroundColor: 'rgba(0, 0, 0, 0.3)',
    borderWidth: 1,
    borderColor: 'rgba(37, 37, 37, 0.6)',
  },
  typeButtonActive: {
    backgroundColor: 'rgba(29, 209, 161, 0.15)',
    borderColor: '#1DD1A1',
  },
  typeButtonText: {
    fontSize: 13,
    color: '#9CA3AF',
    fontFamily: 'JetBrainsMono_600SemiBold',
  },
  typeButtonTextActive: {
    color: '#1DD1A1',
  },
  modalButtons: {
    flexDirection: 'row',
    gap: 12,
    marginTop: 8,
  },
  modalButton: {
    flex: 1,
    paddingVertical: 12,
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
  },
  cancelButton: {
    backgroundColor: 'rgba(0, 0, 0, 0.3)',
    borderWidth: 1,
    borderColor: 'rgba(37, 37, 37, 0.6)',
  },
  cancelButtonText: {
    fontSize: 14,
    fontFamily: 'JetBrainsMono_600SemiBold',
    color: '#9CA3AF',
  },
  uploadButtonModal: {
    backgroundColor: '#1DD1A1',
  },
  uploadButtonText: {
    fontSize: 14,
    fontFamily: 'JetBrainsMono_600SemiBold',
    color: '#000',
  },
});
