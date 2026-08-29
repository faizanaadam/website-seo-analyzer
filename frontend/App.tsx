import React, { useState } from 'react';
import {
  StyleSheet,
  Text,
  View,
  TextInput,
  TouchableOpacity,
  ActivityIndicator,
  SafeAreaView,
  ScrollView,
  StatusBar,
} from 'react-native';
import { ApiService } from './src/services/api';
import { API_CONFIG } from './src/config';
import { ConnectionStatus } from './src/types/analysis';

export default function App() {
  const [backendUrl, setBackendUrl] = useState<string>(API_CONFIG.DEFAULT_BASE_URL);
  const [status, setStatus] = useState<ConnectionStatus>('idle');
  const [statusMessage, setStatusMessage] = useState<string>('Press "Check Backend" to test connection.');
  const [serverDetails, setServerDetails] = useState<string | null>(null);

  const handleCheckBackend = async () => {
    setStatus('checking');
    setStatusMessage('Connecting to backend...');
    setServerDetails(null);

    try {
      const response = await ApiService.checkHealth(backendUrl);
      setStatus('connected');
      setStatusMessage('Backend Connected');
      setServerDetails(`Status: ${response.status}\nMessage: "${response.message}"`);
    } catch (err: any) {
      setStatus('error');
      setStatusMessage('Unable to connect to backend');
      setServerDetails(
        `Error: ${err.message || 'Network request failed'}\n\nTip: If testing on a physical phone via Expo Go, ensure both your phone and PC are on the same Wi-Fi and use your PC's LAN IP (e.g. http://192.168.1.X:8000).`
      );
    }
  };

  const handleTestPostEndpoint = async () => {
    setStatus('checking');
    setStatusMessage('Testing POST /api/analyse endpoint...');
    setServerDetails(null);

    try {
      const response = await ApiService.testAnalyse('https://example.com', backendUrl);
      setStatus('connected');
      setStatusMessage('POST /api/analyse Connected');
      setServerDetails(
        `Status: ${response.status}\nTarget URL: ${response.target_url}\nMessage: "${response.message}"`
      );
    } catch (err: any) {
      setStatus('error');
      setStatusMessage('POST /api/analyse Failed');
      setServerDetails(`Error: ${err.message}`);
    }
  };

  return (
    <SafeAreaView style={styles.safeArea}>
      <StatusBar barStyle="light-content" backgroundColor="#0F172A" />
      <ScrollView contentContainerStyle={styles.container}>
        {/* Header */}
        <View style={styles.header}>
          <Text style={styles.tagline}>PHASE 1 FOUNDATION</Text>
          <Text style={styles.title}>Website SEO & Visibility Analyser</Text>
          <Text style={styles.subtitle}>
            Mobile client and FastAPI backend connection testing harness.
          </Text>
        </View>

        {/* Status Card */}
        <View style={styles.card}>
          <Text style={styles.sectionLabel}>BACKEND CONNECTION</Text>

          <View style={styles.statusRow}>
            <View
              style={[
                styles.statusIndicator,
                status === 'connected' && styles.statusIndicatorSuccess,
                status === 'error' && styles.statusIndicatorError,
                status === 'checking' && styles.statusIndicatorChecking,
              ]}
            />
            <Text style={styles.statusTitle}>{statusMessage}</Text>
          </View>

          {/* Configurable URL */}
          <View style={styles.inputGroup}>
            <Text style={styles.inputLabel}>Backend API Base URL</Text>
            <TextInput
              style={styles.input}
              value={backendUrl}
              onChangeText={setBackendUrl}
              placeholder="http://192.168.1.X:8000"
              placeholderTextColor="#64748B"
              autoCapitalize="none"
              autoCorrect={false}
            />
            <Text style={styles.helpText}>
              For physical phone: Use your PC local LAN IP (e.g. http://192.168.1.15:8000)
            </Text>
          </View>

          {/* Action Buttons */}
          <TouchableOpacity
            style={[styles.primaryButton, status === 'checking' && styles.buttonDisabled]}
            onPress={handleCheckBackend}
            disabled={status === 'checking'}
            activeOpacity={0.8}
          >
            {status === 'checking' ? (
              <ActivityIndicator color="#FFFFFF" size="small" />
            ) : (
              <Text style={styles.primaryButtonText}>Check Backend (GET /health)</Text>
            )}
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.secondaryButton}
            onPress={handleTestPostEndpoint}
            disabled={status === 'checking'}
            activeOpacity={0.8}
          >
            <Text style={styles.secondaryButtonText}>Test POST /api/analyse</Text>
          </TouchableOpacity>

          {/* Server Response Details */}
          {serverDetails ? (
            <View
              style={[
                styles.detailsBox,
                status === 'connected' ? styles.detailsBoxSuccess : styles.detailsBoxError,
              ]}
            >
              <Text style={styles.detailsText}>{serverDetails}</Text>
            </View>
          ) : null}
        </View>

        {/* Phase 1 Verification Card */}
        <View style={styles.infoCard}>
          <Text style={styles.infoTitle}>Phase 1 Deliverables Status</Text>
          <Text style={styles.infoItem}>✓ Git repository initialized</Text>
          <Text style={styles.infoItem}>✓ FastAPI backend running with CORS</Text>
          <Text style={styles.infoItem}>✓ Configurable endpoint without hardcoded secrets</Text>
          <Text style={styles.infoItem}>✓ Expo React Native TypeScript setup verified</Text>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: '#0F172A',
  },
  container: {
    padding: 24,
    paddingTop: 36,
  },
  header: {
    marginBottom: 28,
  },
  tagline: {
    fontSize: 12,
    fontWeight: '700',
    color: '#38BDF8',
    letterSpacing: 1.2,
    marginBottom: 6,
  },
  title: {
    fontSize: 26,
    fontWeight: '800',
    color: '#F8FAFC',
    lineHeight: 32,
  },
  subtitle: {
    fontSize: 14,
    color: '#94A3B8',
    marginTop: 8,
    lineHeight: 20,
  },
  card: {
    backgroundColor: '#1E293B',
    borderRadius: 16,
    padding: 20,
    borderWidth: 1,
    borderColor: '#334155',
    marginBottom: 20,
  },
  sectionLabel: {
    fontSize: 11,
    fontWeight: '700',
    color: '#64748B',
    letterSpacing: 1,
    marginBottom: 14,
  },
  statusRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 20,
  },
  statusIndicator: {
    width: 12,
    height: 12,
    borderRadius: 6,
    backgroundColor: '#64748B',
    marginRight: 10,
  },
  statusIndicatorSuccess: {
    backgroundColor: '#22C55E',
  },
  statusIndicatorError: {
    backgroundColor: '#EF4444',
  },
  statusIndicatorChecking: {
    backgroundColor: '#F59E0B',
  },
  statusTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#F8FAFC',
  },
  inputGroup: {
    marginBottom: 18,
  },
  inputLabel: {
    fontSize: 13,
    fontWeight: '500',
    color: '#CBD5E1',
    marginBottom: 8,
  },
  input: {
    backgroundColor: '#0F172A',
    borderRadius: 10,
    borderWidth: 1,
    borderColor: '#334155',
    paddingHorizontal: 14,
    paddingVertical: 12,
    color: '#F8FAFC',
    fontSize: 14,
  },
  helpText: {
    fontSize: 12,
    color: '#64748B',
    marginTop: 6,
    lineHeight: 16,
  },
  primaryButton: {
    backgroundColor: '#0284C7',
    borderRadius: 10,
    paddingVertical: 14,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 10,
  },
  buttonDisabled: {
    opacity: 0.6,
  },
  primaryButtonText: {
    color: '#FFFFFF',
    fontSize: 15,
    fontWeight: '600',
  },
  secondaryButton: {
    backgroundColor: '#334155',
    borderRadius: 10,
    paddingVertical: 12,
    alignItems: 'center',
    justifyContent: 'center',
  },
  secondaryButtonText: {
    color: '#E2E8F0',
    fontSize: 14,
    fontWeight: '500',
  },
  detailsBox: {
    marginTop: 18,
    padding: 14,
    borderRadius: 10,
    borderWidth: 1,
  },
  detailsBoxSuccess: {
    backgroundColor: '#052E16',
    borderColor: '#15803D',
  },
  detailsBoxError: {
    backgroundColor: '#450A0A',
    borderColor: '#991B1B',
  },
  detailsText: {
    fontSize: 13,
    color: '#F8FAFC',
    lineHeight: 18,
  },
  infoCard: {
    backgroundColor: '#1E293B',
    borderRadius: 14,
    padding: 18,
    borderWidth: 1,
    borderColor: '#334155',
  },
  infoTitle: {
    fontSize: 14,
    fontWeight: '700',
    color: '#E2E8F0',
    marginBottom: 12,
  },
  infoItem: {
    fontSize: 13,
    color: '#94A3B8',
    marginBottom: 6,
  },
});
