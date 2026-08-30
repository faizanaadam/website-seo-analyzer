import { HealthResponse, AnalysisRequest, AnalysisResponse, AnalysisApiResponse } from '../types/analysis';
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
   * Performs full website analysis calling backend POST /api/analyse
   */
  static async analyseWebsite(
    targetUrl: string,
    baseUrl: string = API_CONFIG.DEFAULT_BASE_URL
  ): Promise<AnalysisApiResponse> {
    const cleanUrl = baseUrl.replace(/\/+$/, '');
    const endpoint = `${cleanUrl}/api/analyse`;

    const payload: AnalysisRequest = { url: targetUrl };

    const controller = new AbortController();
    // Allow up to 45 seconds for multi-page crawling and Google PageSpeed Insights
    const timeoutId = setTimeout(() => controller.abort(), 45000);

    try {
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        body: JSON.stringify(payload),
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        let errorDetail = `Server returned HTTP ${response.status}`;
        try {
          const errData = await response.json();
          if (errData.detail) errorDetail = errData.detail;
        } catch (e) {
          // ignore
        }
        throw new Error(errorDetail);
      }

      const data: AnalysisApiResponse = await response.json();
      return data;
    } catch (error: any) {
      clearTimeout(timeoutId);
      if (error.name === 'AbortError') {
        throw new Error('Analysis timed out after 45 seconds. The target website may be very slow to respond.');
      }
      throw error;
    }
  }

  /**
   * Test initial /api/analyse placeholder endpoint (backwards compatible)
   */
  static async testAnalyse(
    targetUrl: string,
    baseUrl: string = API_CONFIG.DEFAULT_BASE_URL
  ): Promise<AnalysisResponse> {
    return this.analyseWebsite(targetUrl, baseUrl);
  }
}

