import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

import { environment } from '../../environments/environment';

export type ExportFormat = 'json' | 'csv';

export interface Resource {
  id: number;
  resource_type: string;
  url: string | null;
  host: string | null;
  integrity: string | null;
  crossorigin: string | null;
  async_attr: boolean;
  defer_attr: boolean;
  provider: string | null;
  category: string | null;
}

export interface ContentAnalysis {
  id: number;
  target: string;
  status: string;
  analysis_type: string;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  error_message: string | null;
  page_title: string | null;
  resources: Resource[];
}

export interface AnalysisListItem {
  id: number;
  target: string;
  status: string;
  analysis_type: string;
  created_at: string;
  page_title: string | null;
  resource_count: number;
  script_count: number;
  iframe_count: number;
  stylesheet_count: number;
  preconnect_count: number;
}

export interface InventoryResponse {
  analysis: ContentAnalysis;
  resource_count: number;
  script_count: number;
  iframe_count: number;
  stylesheet_count: number;
  preconnect_count: number;
}

export interface HealthResponse {
  status: string;
  database: string;
  version: string;
  tool: string;
}

/** xwa-sdk Event envelope as received over the WebSocket. */
export interface LiveEvent {
  seq: number;
  type: string;
  tool: string;
  analysis_id: string;
  ts: string;
  payload: unknown;
}

/** Payload shapes emitted by the musha live stream. */
export interface StartedPayload {
  target?: string;
}

export interface ProgressPayload {
  page?: string;
  title?: string | null;
}

export interface ItemFoundPayload {
  kind?: string;
  url?: string | null;
  provider?: string | null;
}

export interface LiveErrorPayload {
  /** xwa-sdk Error object emitted top-level by the backend. */
  code?: string;
  message?: string;
  retryable?: boolean;
  /** Also tolerate a nested REST-style `{ error: { message } }` payload. */
  error?: {
    code?: string;
    message?: string;
    retryable?: boolean;
  };
}

/** Known live event types of the xwa-sdk Event contract. */
export const LIVE_EVENT_TYPES = [
  'analysis_started',
  'analysis_progress',
  'item_found',
  'analysis_completed',
  'analysis_error',
] as const;

@Injectable({ providedIn: 'root' })
export class ApiService {
  private readonly http = inject(HttpClient);
  private readonly apiUrl = environment.apiBaseUrl;
  private readonly wsUrl = environment.wsBaseUrl;

  health(): Observable<HealthResponse> {
    return this.http.get<HealthResponse>(`${this.apiUrl}/api/health`);
  }

  /** Synchronous REST fallback (the live WebSocket is the preferred path). */
  inventory(target: string): Observable<InventoryResponse> {
    return this.http.post<InventoryResponse>(`${this.apiUrl}/api/content/inventory`, {
      target,
    });
  }

  listAnalyses(): Observable<AnalysisListItem[]> {
    return this.http.get<AnalysisListItem[]>(`${this.apiUrl}/api/analyses`);
  }

  getAnalysis(id: number | string): Observable<ContentAnalysis> {
    return this.http.get<ContentAnalysis>(`${this.apiUrl}/api/analyses/${id}`);
  }

  deleteAnalysis(id: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/api/analyses/${id}`);
  }

  deleteAllAnalyses(): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/api/analyses`);
  }

  /** Server-side export URL (Content-Disposition attachment). */
  exportUrl(id: number, format: ExportFormat = 'json'): string {
    return `${this.apiUrl}/api/analyses/${id}/export?format=${format}`;
  }

  /** Live WebSocket endpoint (target URL-encoded). */
  liveUrl(target: string): string {
    return `${this.wsUrl}/api/content/live?target=${encodeURIComponent(target)}`;
  }
}
