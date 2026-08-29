import { HealthResponse, AnalysisRequest, AnalysisResponse } from '../types/analysis';
import { API_CONFIG } from '../config';

export class ApiService {
  /**
   * Test health check endpoint on the backend
   */
  static async checkHealth(baseUrl: string = API_CONFIG.DEFAULT_BASE_URL): Promise<HealthResponse> {
    const cleanUrl = baseUrl.replace(/\/+$/, '');
    const endpoint = `${cleanUrl}/health`;

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), API_CONFIG.TIMEOUT_MS);

    try {
      const response = await fetch(endpoint, {
        method: 'GET',
        headers: {
          'Accept': 'application/json',
        },
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        throw new Error(`Server returned HTTP ${response.status}: ${response.statusText}`);
      }

      const data: HealthResponse = await response.json();
      return data;
    } catch (error: any) {
      clearTimeout(timeoutId);
      if (error.name === 'AbortError') {
        throw new Error('Connection timed out after 10 seconds. Check if the server is running and accessible.');
      }
      throw error;
    }
  }

  /**
   * Test initial /api/analyse placeholder endpoint
   */
  static async testAnalyse(
    targetUrl: string,
    baseUrl: string = API_CONFIG.DEFAULT_BASE_URL
  ): Promise<AnalysisResponse> {
    const cleanUrl = baseUrl.replace(/\/+$/, '');
    const endpoint = `${cleanUrl}/api/analyse`;

    const payload: AnalysisRequest = { url: targetUrl };

    const response = await fetch(endpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      throw new Error(`Analysis test returned HTTP ${response.status}`);
    }

    return response.json();
  }
}
