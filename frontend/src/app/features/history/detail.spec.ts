import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { of } from 'rxjs';

import { ApiService, ContentAnalysis } from '../../core/api.service';
import { XwaChartDatum } from '../../shared/charts/xwa-chart.component';
import { AnalysisDetailComponent } from './detail';

const analysis = {
  id: 7,
  target: 'https://example.com',
  status: 'COMPLETED',
  analysis_type: 'content_scan',
  created_at: '2026-09-20T10:00:00',
  started_at: null,
  finished_at: null,
  error_message: null,
  page_title: 'Example',
  resources: [
    {
      id: 1,
      resource_type: 'script',
      url: 'https://www.googletagmanager.com/gtag/js',
      host: 'www.googletagmanager.com',
      integrity: null,
      crossorigin: null,
      async_attr: true,
      defer_attr: false,
      provider: 'Google Tag Manager',
      category: 'tag-manager',
    },
    {
      id: 2,
      resource_type: 'script',
      url: 'https://cdn.jsdelivr.net/npm/lodash/lodash.min.js',
      host: 'cdn.jsdelivr.net',
      integrity: 'sha384-abc',
      crossorigin: 'anonymous',
      async_attr: false,
      defer_attr: true,
      provider: 'jsDelivr',
      category: 'cdn',
    },
    {
      id: 3,
      resource_type: 'stylesheet',
      url: 'https://example.com/app.css',
      host: 'example.com',
      integrity: null,
      crossorigin: null,
      async_attr: false,
      defer_attr: false,
      provider: null,
      category: null,
    },
  ],
} as unknown as ContentAnalysis;

const otherItems = [
  {
    id: 9,
    target: 'https://example.com',
    status: 'COMPLETED',
    analysis_type: 'content_scan',
    created_at: '2026-09-21T10:00:00',
    page_title: null,
    resource_count: 4,
    script_count: 2,
    iframe_count: 1,
    stylesheet_count: 1,
    preconnect_count: 0,
  },
];

const diffResponse = {
  base: { id: 7, target: 'https://example.com', created_at: '2026-09-20T10:00:00' },
  against: { id: 9, target: 'https://example.com', created_at: '2026-09-21T10:00:00' },
  summary: {
    base_total: 3,
    other_total: 4,
    added_count: 1,
    removed_count: 0,
    modified_count: 1,
    unchanged_count: 2,
    provider_changes_count: 0,
    similarity_score: 57.1,
  },
  added: [
    {
      resource_type: 'iframe',
      url: 'https://player.example.com/embed',
      host: 'player.example.com',
      integrity: null,
      crossorigin: null,
      async_attr: false,
      defer_attr: false,
      provider: null,
      category: null,
    },
  ],
  removed: [],
  modified: [],
  provider_changes: [],
};

const driftResponse = {
  domain: 'example.com',
  first_created_at: '2026-09-20T10:00:00',
  last_created_at: '2026-09-21T10:00:00',
  summary: {
    analysis_count: 2,
    severity: 'medium',
    total_resource_delta: 1,
    providers_added: [],
    providers_removed: [],
    alert: 'Moderate drift: resource count +1 (+33.3%).',
  },
  steps: [
    {
      from_analysis_id: 7,
      to_analysis_id: 9,
      from_created_at: '2026-09-20T10:00:00',
      to_created_at: '2026-09-21T10:00:00',
      resource_delta: 1,
      resource_delta_pct: 33.3,
      providers_added: [],
      providers_removed: [],
      severity: 'medium',
      alert: 'Moderate drift: resource count +1 (+33.3%).',
    },
  ],
};

describe('AnalysisDetailComponent', () => {
  let fixture: ComponentFixture<AnalysisDetailComponent>;
  let component: any;
  const apiStub = {
    listAnalyses: vi.fn(() => of(otherItems)),
    getAnalysis: vi.fn(() => of(analysis)),
    diff: vi.fn(() => of(diffResponse)),
    drift: vi.fn(() => of(driftResponse)),
    exportUrl: vi.fn(() => ''),
  };

  beforeEach(async () => {
    localStorage.clear();
    apiStub.diff.mockClear();
    apiStub.drift.mockClear();
    apiStub.listAnalyses.mockReturnValue(of(otherItems));

    await TestBed.configureTestingModule({
      imports: [AnalysisDetailComponent],
      providers: [provideRouter([]), { provide: ApiService, useValue: apiStub }],
    }).compileComponents();

    fixture = TestBed.createComponent(AnalysisDetailComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput('analysis', analysis);
    fixture.detectChanges();
    await fixture.whenStable();
  });

  it('should render the three analysis charts with SVG data', () => {
    const host = fixture.nativeElement as HTMLElement;
    const charts = Array.from(host.querySelectorAll('app-xwa-chart'));
    expect(charts.length).toBe(3);
    for (const chart of charts) {
      expect(chart.querySelector('svg')).toBeTruthy();
    }
    // donut center total shows the resource count
    const texts = Array.from(host.querySelectorAll('svg text')).map((node) =>
      node.textContent?.trim(),
    );
    expect(texts).toContain('3');
    expect(texts).toContain('ASYNC');
  });

  it('should compute chart series from resources', () => {
    const donut = component.resourceTypeDonut();
    expect(donut.map((datum: XwaChartDatum) => datum.label)).toEqual(['SCRIPT', 'STYLESHEET']);
    expect(donut[0].value).toBe(2);
    expect(component.providersByCategory()[0].label).toBe('Google Tag Manager');
    const flags = component.attributeFlagBars();
    expect(flags.find((datum: XwaChartDatum) => datum.label === 'ASYNC')?.value).toBe(1);
    expect(flags.find((datum: XwaChartDatum) => datum.label === 'SRI')?.value).toBe(1);
  });

  it('should run a structural diff against the selected analysis', async () => {
    component.diffAgainstId = 9;
    component.runDiff();
    await fixture.whenStable();

    expect(apiStub.diff).toHaveBeenCalledWith(7, 9);
    expect(component.diffResult?.summary.similarity_score).toBe(57.1);
    fixture.detectChanges();
    const host = fixture.nativeElement as HTMLElement;
    expect(host.textContent).toContain('STRUCTURAL DIFF');
    expect(host.textContent).toContain('player.example.com');
  });

  it('should load drift for the analysis domain', async () => {
    expect(component.domainOf()).toBe('example.com');
    component.runDrift();
    await fixture.whenStable();

    expect(apiStub.drift).toHaveBeenCalledWith('example.com');
    expect(component.driftResult?.summary.severity).toBe('medium');
    fixture.detectChanges();
    const host = fixture.nativeElement as HTMLElement;
    expect(host.textContent).toContain('CONTENT DRIFT');
    expect(host.textContent).toContain('MEDIUM');
  });
});
