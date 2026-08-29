import { Platform } from 'react-native';

/**
 * Default API Base URL.
 * - On Web / iOS Simulator: http://localhost:8000
 * - On Android Emulator: http://10.0.2.2:8000
 * - On Physical Device with Expo Go: Change this to your computer's LAN IP, e.g. http://192.168.1.50:8000
 */
const getDefaultBaseUrl = (): string => {
  if (Platform.OS === 'android') {
    return 'http://10.0.2.2:8000';
  }
  return 'http://localhost:8000';
};

export const API_CONFIG = {
  DEFAULT_BASE_URL: getDefaultBaseUrl(),
  TIMEOUT_MS: 10000,
};
