import { Platform } from 'react-native';

/**
 * Default API Base URL.
 * - On Web (localhost or LAN IP): dynamically connects to :8000 on the same host
 * - On Android Emulator: http://10.0.2.2:8000
 * - On iOS Simulator / Localhost: http://localhost:8000
 */
const getDefaultBaseUrl = (): string => {
  if (typeof window !== 'undefined' && window.location && window.location.hostname) {
    const host = window.location.hostname;
    return `http://${host}:8000`;
  }
  if (Platform.OS === 'android') {
    return 'http://10.0.2.2:8000';
  }
  return 'http://localhost:8000';
};

export const API_CONFIG = {
  DEFAULT_BASE_URL: getDefaultBaseUrl(),
  TIMEOUT_MS: 45000,
};

