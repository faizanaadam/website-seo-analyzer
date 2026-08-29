export interface HealthResponse {
  status: string;
  message: string;
}

export interface AnalysisRequest {
  url: string;
}

export interface AnalysisResponse {
  status: string;
  message: string;
  target_url: string;
}

export type ConnectionStatus = 'idle' | 'checking' | 'connected' | 'error';
