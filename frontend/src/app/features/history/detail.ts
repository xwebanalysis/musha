import { CommonModule } from '@angular/common';
import { ChangeDetectorRef, Component, Input, OnInit, inject } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';

import { ApiService, ContentAnalysis } from '../../core/api.service';
import { I18nService } from '../../core/i18n.service';
import { DetailColumn, DetailTableComponent } from '../../shared/detail-table/detail-table';
import { ExportActionsComponent } from '../../shared/export-actions/export-actions';
import { MetricCardComponent } from '../../shared/metric-card/metric-card';
import { StatusBadgeComponent } from '../../shared/status-badge/status-badge';

@Component({
  selector: 'app-analysis-detail',
  standalone: true,
  imports: [
    CommonModule,
    RouterLink,
    DetailTableComponent,
    ExportActionsComponent,
    MetricCardComponent,
    StatusBadgeComponent,
  ],
  templateUrl: './detail.html',
  styleUrl: './detail.scss',
})
export class AnalysisDetailComponent implements OnInit {
  @Input() analysis: ContentAnalysis | null = null;

  private readonly route = inject(ActivatedRoute);
  private readonly api = inject(ApiService);
  private readonly i18n = inject(I18nService);
  private readonly cdr = inject(ChangeDetectorRef);

  protected loading = false;
  protected error: string | null = null;
  protected routeView = false;

  protected readonly scriptColumns: DetailColumn[] = [
    { key: 'provider', label: 'PROVIDER' },
    { key: 'category', label: 'CATEGORY' },
    { key: 'url', label: 'URL' },
    { key: 'integrity', label: 'SRI' },
    { key: 'crossorigin', label: 'CROSSORIGIN' },
    { key: 'async_attr', label: 'ASYNC' },
    { key: 'defer_attr', label: 'DEFER' },
  ];

  protected readonly styleColumns: DetailColumn[] = [
    { key: 'provider', label: 'PROVIDER' },
    { key: 'category', label: 'CATEGORY' },
    { key: 'url', label: 'URL' },
    { key: 'integrity', label: 'SRI' },
    { key: 'crossorigin', label: 'CROSSORIGIN' },
  ];

  protected readonly iframeColumns: DetailColumn[] = [
    { key: 'provider', label: 'PROVIDER' },
    { key: 'category', label: 'CATEGORY' },
    { key: 'url', label: 'URL' },
  ];

  protected readonly preconnectColumns: DetailColumn[] = [
    { key: 'host', label: 'HOST' },
    { key: 'url', label: 'URL' },
    { key: 'crossorigin', label: 'CROSSORIGIN' },
  ];

  protected readonly otherColumns: DetailColumn[] = [
    { key: 'resource_type', label: 'TYPE' },
    { key: 'provider', label: 'PROVIDER' },
    { key: 'host', label: 'HOST' },
    { key: 'url', label: 'URL' },
  ];

  private readonly knownTypes = ['script', 'stylesheet', 'iframe', 'preconnect'];

  ngOnInit(): void {
    if (this.analysis) {
      return;
    }
    const id = this.route.snapshot.paramMap.get('id');
    if (!id) {
      return;
    }
    this.routeView = true;
    this.loading = true;
    this.error = null;
    this.api.getAnalysis(id).subscribe({
      next: (analysis) => {
        this.analysis = analysis;
        this.loading = false;
        this.cdr.markForCheck();
      },
      error: () => {
        this.error = this.i18n.t('error.backend');
        this.loading = false;
        this.cdr.markForCheck();
      },
    });
  }

  protected t(key: string): string {
    return this.i18n.t(key);
  }

  protected resourcesOf(type: string): object[] {
    return this.analysis?.resources.filter((resource) => resource.resource_type === type) ?? [];
  }

  protected otherResources(): object[] {
    return (
      this.analysis?.resources.filter(
        (resource) => !this.knownTypes.includes(resource.resource_type),
      ) ?? []
    );
  }

  protected counts(): { scripts: number; stylesheets: number; iframes: number; preconnects: number } {
    return {
      scripts: this.resourcesOf('script').length,
      stylesheets: this.resourcesOf('stylesheet').length,
      iframes: this.resourcesOf('iframe').length,
      preconnects: this.resourcesOf('preconnect').length,
    };
  }
}
