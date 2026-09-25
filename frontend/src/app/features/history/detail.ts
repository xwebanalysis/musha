import { CommonModule } from '@angular/common';
import { ChangeDetectorRef, Component, Input, OnInit, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';

import {
  AnalysisListItem,
  ApiService,
  ContentAnalysis,
  DiffResponse,
  DriftResponse,
} from '../../core/api.service';
import { I18nService } from '../../core/i18n.service';
import {
  XwaChartColorKey,
  XwaChartComponent,
  XwaChartDatum,
} from '../../shared/charts/xwa-chart.component';
import { DetailColumn, DetailTableComponent } from '../../shared/detail-table/detail-table';
import { ExportActionsComponent } from '../../shared/export-actions/export-actions';
import { MetricCardComponent } from '../../shared/metric-card/metric-card';
import { StatusBadgeComponent } from '../../shared/status-badge/status-badge';

const CATEGORY_COLORS: Record<string, XwaChartColorKey> = {
  'tag-manager': 'interactive',
  analytics: 'info',
  ads: 'warning',
  cdn: 'success',
  social: 'critical',
  monitoring: 'neutral-strong',
  fonts: 'info',
  captcha: 'warning',
  testing: 'neutral',
  support: 'neutral',
  cms: 'neutral-strong',
  ecommerce: 'warning',
  cloud: 'info',
  search: 'neutral',
};

const TYPE_COLORS: Record<string, XwaChartColorKey> = {
  script: 'interactive',
  stylesheet: 'warning',
  iframe: 'success',
  preconnect: 'info',
  other: 'neutral-strong',
};

@Component({
  selector: 'app-analysis-detail',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    RouterLink,
    DetailTableComponent,
    ExportActionsComponent,
    MetricCardComponent,
    StatusBadgeComponent,
    XwaChartComponent,
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

  protected analyses: AnalysisListItem[] = [];
  protected diffAgainstId: number | null = null;
  protected diffResult: DiffResponse | null = null;
  protected diffLoading = false;
  protected diffError: string | null = null;

  protected driftResult: DriftResponse | null = null;
  protected driftLoading = false;
  protected driftError: string | null = null;

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

  protected readonly diffEntryColumns: DetailColumn[] = [
    { key: 'resource_type', label: 'TYPE' },
    { key: 'provider', label: 'PROVIDER' },
    { key: 'category', label: 'CATEGORY' },
    { key: 'url', label: 'URL' },
  ];

  protected readonly diffModifiedColumns: DetailColumn[] = [
    { key: 'resource_type', label: 'TYPE' },
    { key: 'url', label: 'URL' },
    { key: 'changes', label: 'CHANGES' },
    { key: 'provider', label: 'PROVIDER' },
  ];

  private readonly knownTypes = ['script', 'stylesheet', 'iframe', 'preconnect'];

  ngOnInit(): void {
    if (!this.analysis) {
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
    this.loadAnalyses();
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

  // -------------------------------------------------------------------------
  // Charts
  // -------------------------------------------------------------------------

  protected resourceTypeDonut(): XwaChartDatum[] {
    const byType = new Map<string, number>();
    for (const resource of this.analysis?.resources ?? []) {
      const key = this.knownTypes.includes(resource.resource_type) ? resource.resource_type : 'other';
      byType.set(key, (byType.get(key) ?? 0) + 1);
    }
    return [...byType.entries()]
      .map(([label, value]) => ({
        label: label.toUpperCase(),
        value,
        color: TYPE_COLORS[label] ?? 'neutral',
      }))
      .sort((a, b) => b.value - a.value);
  }

  protected providersByCategory(): XwaChartDatum[] {
    const byProvider = new Map<string, { count: number; category: string | null }>();
    for (const resource of this.analysis?.resources ?? []) {
      if (!resource.provider) {
        continue;
      }
      const entry = byProvider.get(resource.provider) ?? { count: 0, category: resource.category };
      entry.count += 1;
      byProvider.set(resource.provider, entry);
    }
    return [...byProvider.entries()]
      .map(([label, entry]) => ({
        label,
        value: entry.count,
        color: CATEGORY_COLORS[entry.category ?? ''] ?? 'neutral',
      }))
      .sort((a, b) => b.value - a.value)
      .slice(0, 8);
  }

  protected attributeFlagBars(): XwaChartDatum[] {
    const resources = this.analysis?.resources ?? [];
    return [
      {
        label: 'ASYNC',
        value: resources.filter((resource) => resource.async_attr).length,
        color: 'interactive',
      },
      {
        label: 'DEFER',
        value: resources.filter((resource) => resource.defer_attr).length,
        color: 'info',
      },
      {
        label: 'SRI',
        value: resources.filter((resource) => !!resource.integrity).length,
        color: 'success',
      },
      {
        label: 'CROSSORIGIN',
        value: resources.filter((resource) => !!resource.crossorigin).length,
        color: 'warning',
      },
    ];
  }

  // -------------------------------------------------------------------------
  // Structural diff
  // -------------------------------------------------------------------------

  protected loadAnalyses(): void {
    this.api.listAnalyses().subscribe({
      next: (items) => {
        this.analyses = items;
        this.cdr.markForCheck();
      },
      error: () => {
        this.analyses = [];
        this.cdr.markForCheck();
      },
    });
  }

  protected diffableAnalyses(): AnalysisListItem[] {
    return this.analyses.filter((item) => item.id !== this.analysis?.id);
  }

  protected canRunDiff(): boolean {
    return this.diffAgainstId !== null && !this.diffLoading;
  }

  protected runDiff(): void {
    if (!this.analysis || this.diffAgainstId === null) {
      return;
    }
    this.diffLoading = true;
    this.diffError = null;
    this.diffResult = null;
    this.api.diff(this.analysis.id, this.diffAgainstId).subscribe({
      next: (result) => {
        this.diffResult = result;
        this.diffLoading = false;
        this.cdr.markForCheck();
      },
      error: () => {
        this.diffError = this.t('error.backend');
        this.diffLoading = false;
        this.cdr.markForCheck();
      },
    });
  }

  protected diffModifiedRows(): object[] {
    return (this.diffResult?.modified ?? []).map((entry) => ({
      resource_type: entry.resource_type,
      url: entry.url,
      changes: entry.changes.map((change) => change.toUpperCase()).join(', '),
      provider: entry.provider_changed
        ? `${entry.provider_base ?? 'NONE'} → ${entry.provider_other ?? 'NONE'}`
        : entry.provider_base ?? '—',
    }));
  }

  protected providerChangeRows(): object[] {
    return (this.diffResult?.provider_changes ?? []).map((entry) => ({
      resource_type: entry.resource_type,
      url: entry.url,
      changes: 'PROVIDER',
      provider: `${entry.provider_base ?? 'NONE'} → ${entry.provider_other ?? 'NONE'}`,
    }));
  }

  // -------------------------------------------------------------------------
  // Content drift
  // -------------------------------------------------------------------------

  protected domainOf(): string {
    const target = this.analysis?.target ?? '';
    try {
      const withScheme = target.includes('://') ? target : `https://${target}`;
      return new URL(withScheme).hostname.toLowerCase().replace(/^www\./, '');
    } catch {
      return target.toLowerCase().replace(/^www\./, '');
    }
  }

  protected canRunDrift(): boolean {
    return !!this.domainOf() && !this.driftLoading;
  }

  protected runDrift(): void {
    const domain = this.domainOf();
    if (!domain) {
      return;
    }
    this.driftLoading = true;
    this.driftError = null;
    this.driftResult = null;
    this.api.drift(domain).subscribe({
      next: (result) => {
        this.driftResult = result;
        this.driftLoading = false;
        this.cdr.markForCheck();
      },
      error: () => {
        this.driftError = this.t('error.backend');
        this.driftLoading = false;
        this.cdr.markForCheck();
      },
    });
  }

  protected severityClass(severity: string): string {
    if (severity === 'high') {
      return 'text-accent';
    }
    if (severity === 'medium') {
      return 'text-warning';
    }
    return 'text-success';
  }

  protected driftSteps(): object[] {
    return (this.driftResult?.steps ?? []).map((step) => ({
      from_analysis_id: `#${step.from_analysis_id}`,
      to_analysis_id: `#${step.to_analysis_id}`,
      resource_delta: `${step.resource_delta > 0 ? '+' : ''}${step.resource_delta} (${step.resource_delta_pct === null ? 'n/a' : `${step.resource_delta_pct}%`})`,
      providers_added: step.providers_added.join(', ') || '—',
      providers_removed: step.providers_removed.join(', ') || '—',
      severity: step.severity.toUpperCase(),
      alert: step.alert,
    }));
  }

  protected readonly driftColumns: DetailColumn[] = [
    { key: 'from_analysis_id', label: 'FROM' },
    { key: 'to_analysis_id', label: 'TO' },
    { key: 'resource_delta', label: 'RESOURCES' },
    { key: 'providers_added', label: 'PROVIDERS +' },
    { key: 'providers_removed', label: 'PROVIDERS -' },
    { key: 'severity', label: 'SEVERITY' },
    { key: 'alert', label: 'ALERT' },
  ];
}
