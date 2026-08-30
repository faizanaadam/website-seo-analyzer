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
  /** Timeout for lightweight health-check requests (10s). */
  TIMEOUT_MS: 10000,
  /**
   * Overall wall-clock deadline for the full website analysis request (120s).
   * The backend runs PageSpeed (≤45s) and OpenAI (≤45s) as independent
   * concurrent tasks. The total pipeline can legitimately take 60–90s when
   * one external service approaches its individual deadline.
   * This value must always be greater than the sum of the two backend
   * service deadlines plus crawl/content overhead.
   */
  ANALYSIS_TIMEOUT_MS: 120000,
};

