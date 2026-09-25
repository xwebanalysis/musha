import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { of } from 'rxjs';

import { ApiService } from '../../core/api.service';
import { XwaChartDatum } from '../../shared/charts/xwa-chart.component';
import { HistoryComponent } from './history';

const historyItems = [
  {
    id: 3,
    target: 'https://example.com',
    status: 'COMPLETED',
    analysis_type: 'content_scan',
    created_at: '2026-09-22T10:00:00',
    page_title: 'Example',
    resource_count: 2,
    script_count: 1,
    iframe_count: 0,
    stylesheet_count: 1,
    preconnect_count: 0,
  },
  {
    id: 2,
    target: 'https://example.com',
    status: 'ERROR',
    analysis_type: 'content_scan',
    created_at: '2026-09-22T09:00:00',
    page_title: null,
    resource_count: 0,
    script_count: 0,
    iframe_count: 0,
    stylesheet_count: 0,
    preconnect_count: 0,
  },
  {
    id: 1,
    target: 'https://other.example',
    status: 'COMPLETED',
    analysis_type: 'content_scan',
    created_at: '2026-09-20T10:00:00',
    page_title: 'Other',
    resource_count: 4,
    script_count: 3,
    iframe_count: 1,
    stylesheet_count: 0,
    preconnect_count: 0,
  },
];

describe('HistoryComponent', () => {
  let fixture: ComponentFixture<HistoryComponent>;
  let component: any;
  const apiStub = {
    listAnalyses: vi.fn(() => of(historyItems)),
    deleteAnalysis: vi.fn(() => of(void 0)),
    deleteAllAnalyses: vi.fn(() => of(void 0)),
  };

  beforeEach(async () => {
    localStorage.clear();
    apiStub.listAnalyses.mockReturnValue(of(historyItems));

    await TestBed.configureTestingModule({
      imports: [HistoryComponent],
      providers: [provideRouter([]), { provide: ApiService, useValue: apiStub }],
    }).compileComponents();

    fixture = TestBed.createComponent(HistoryComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
    await fixture.whenStable();
  });

  it('should render the scans-per-day line and status donut with SVG data', () => {
    const host = fixture.nativeElement as HTMLElement;
    const charts = Array.from(host.querySelectorAll('app-xwa-chart'));
    expect(charts.length).toBe(2);
    for (const chart of charts) {
      expect(chart.querySelector('svg')).toBeTruthy();
    }
  });

  it('should bucket scans per day in chronological order', () => {
    const series = component.scansPerDay();
    expect(series).toEqual([
      { label: '2026-09-20', value: 1 },
      { label: '2026-09-22', value: 2 },
    ]);
  });

  it('should color the status donut by severity mapping', () => {
    const donut = component.statusDonut();
    const completed = donut.find((datum: XwaChartDatum) => datum.label === 'COMPLETED');
    const error = donut.find((datum: XwaChartDatum) => datum.label === 'ERROR');
    expect(completed?.color).toBe('success');
    expect(error?.color).toBe('critical');
    expect(completed?.value).toBe(2);
    expect(error?.value).toBe(1);
  });
});
