import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

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

export interface InventoryResponse {
  analysis: ContentAnalysis;
  resource_count: number;
  script_count: number;
  iframe_count: number;
  stylesheet_count: number;
}

@Injectable({ providedIn: 'root' })
export class ApiService {
  private readonly http = inject(HttpClient);
  private readonly apiUrl = `http://${window.location.hostname}:8000`;

  health(): Observable<{ status: string; database: string; version: string }> {
    return this.http.get<{ status: string; database: string; version: string }>(
      `${this.apiUrl}/api/health`,
    );
  }

  inventory(target: string): Observable<InventoryResponse> {
    return this.http.post<InventoryResponse>(
      `${this.apiUrl}/api/content/inventory`,
      { target },
    );
  }
}
