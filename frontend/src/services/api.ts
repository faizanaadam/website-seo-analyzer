import { HealthResponse, AnalysisRequest, AnalysisResponse, AnalysisApiResponse } from '../types/analysis';
import { API_CONFIG } from '../config';

export class ApiService {
  /**
   * Test health check endpoint on the backend.
   * Uses API_CONFIG.TIMEOUT_MS (10s) — lightweight, fast-fail.
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
   * Performs full website analysis calling backend POST /api/analyse.
   *
   * Timeout strategy:
   * - Uses API_CONFIG.ANALYSIS_TIMEOUT_MS (120s) as the overall wall-clock deadline.
   * - The backend runs PageSpeed and OpenAI as independent concurrent tasks,
   *   each bounded by their own 45-second service deadline.
   * - The full pipeline can legitimately take 60–90 seconds when a slow external
   *   service approaches its individual deadline.
   * - A 120-second frontend fence ensures we never wait indefinitely, while
   *   also never aborting a valid analysis prematurely.
   */
  static async analyseWebsite(
    targetUrl: string,
    baseUrl: string = API_CONFIG.DEFAULT_BASE_URL
  ): Promise<AnalysisApiResponse> {
    const cleanUrl = baseUrl.replace(/\/+$/, '');
    const endpoint = `${cleanUrl}/api/analyse`;

    const payload: AnalysisRequest = { url: targetUrl };

    const controller = new AbortController();
    // Use ANALYSIS_TIMEOUT_MS (120s). This is intentionally longer than any
    // single backend service deadline so we never abort a valid analysis.
    const timeoutId = setTimeout(() => controller.abort(), API_CONFIG.ANALYSIS_TIMEOUT_MS);

    const startTime = Date.now();

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
          // ignore JSON parse failure on error response
        }
        throw new Error(errorDetail);
      }

      const data: AnalysisApiResponse = await response.json();
      const elapsed = Math.round((Date.now() - startTime) / 1000);
      console.log(`[ApiService] analyseWebsite completed in ${elapsed}s for ${targetUrl}`);
      return data;
    } catch (error: any) {
      clearTimeout(timeoutId);
      const elapsed = Math.round((Date.now() - startTime) / 1000);

      if (error.name === 'AbortError') {
        // The overall 120-second deadline was reached. This is unusual — it
        // means BOTH external services (PageSpeed + OpenAI) were extremely slow
        // or the network was interrupted. Do NOT blame the target website.
        console.warn(`[ApiService] analyseWebsite aborted after ${elapsed}s for ${targetUrl}`);
        throw new Error(
          'The analysis is taking longer than expected and could not be completed. ' +
          'One or more external services (Google PageSpeed, AI insights) may be temporarily unavailable. ' +
          'Please try again in a moment.'
        );
      }

      console.error(`[ApiService] analyseWebsite failed after ${elapsed}s for ${targetUrl}:`, error.message);
      throw error;
    }
  }

  /**
   * Test initial /api/analyse placeholder endpoint (backwards compatible).
   */
  static async testAnalyse(
    targetUrl: string,
    baseUrl: string = API_CONFIG.DEFAULT_BASE_URL
  ): Promise<AnalysisResponse> {
    return this.analyseWebsite(targetUrl, baseUrl);
  }
}
