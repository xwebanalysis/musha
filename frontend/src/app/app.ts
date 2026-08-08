import { Component, OnInit, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';

import { ApiService, ContentAnalysis, Resource } from './services/api.service';
import { ThemeService } from './services/theme.service';

@Component({
  selector: 'app-root',
  imports: [FormsModule, CommonModule],
  templateUrl: './app.html',
  styleUrl: './app.scss',
})
export class App implements OnInit {
  private readonly api = inject(ApiService);
  private readonly theme = inject(ThemeService);

  protected target = '';
  protected loading = false;
  protected error: string | null = null;
  protected backendOnline = false;
  protected analysis: ContentAnalysis | null = null;

  ngOnInit(): void {
    this.theme.initTheme();
    this.api.health().subscribe({
      next: () => (this.backendOnline = true),
      error: () => (this.backendOnline = false),
    });
  }

  toggleTheme(): void {
    this.theme.toggleTheme();
  }

  themeLabel(): string {
    return this.theme.nextThemeLabel();
  }

  analyze(): void {
    const target = this.target.trim();
    if (!target || this.loading) {
      return;
    }
    this.loading = true;
    this.error = null;
    this.api.inventory(target).subscribe({
      next: (response) => {
        this.analysis = response.analysis;
        this.loading = false;
      },
      error: (err) => {
        this.error = err.error?.detail ?? 'Failed to reach the backend.';
        this.loading = false;
      },
    });
  }

  resourcesOf(type: string): Resource[] {
    return this.analysis?.resources.filter((r) => r.resource_type === type) ?? [];
  }

  exportJson(): void {
    if (!this.analysis) {
      return;
    }
    const payload = JSON.stringify(this.analysis, null, 2);
    const blob = new Blob([payload], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `musha-analysis-${this.analysis.id}.json`;
    link.click();
    URL.revokeObjectURL(url);
  }
}
