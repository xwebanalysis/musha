import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { of } from 'rxjs';

import { ApiService, ContentAnalysis } from '../../core/api.service';
import { LiveService } from '../../core/live.service';
import { AnalyzerComponent } from './analyzer';

const analysis = {
  id: 7,
  target: 'https://example.com',
  status: 'COMPLETED',
  analysis_type: 'content_scan',
  created_at: '2026-09-12T10:00:00',
  started_at: null,
  finished_at: null,
  error_message: null,
  page_title: 'Example',
  resources: [],
} as unknown as ContentAnalysis;

describe('AnalyzerComponent', () => {
  let fixture: ComponentFixture<AnalyzerComponent>;
  let component: any;
  const apiStub = {
    inventory: vi.fn(),
    getAnalysis: vi.fn(),
    liveUrl: vi.fn((target: string) => `ws://test/api/content/live?target=${target}`),
  };
  const liveStub = { connect: vi.fn() };

  beforeEach(async () => {
    localStorage.clear();
    apiStub.inventory.mockReset();
    apiStub.getAnalysis.mockReset();
    liveStub.connect.mockReset();

    await TestBed.configureTestingModule({
      imports: [AnalyzerComponent],
      providers: [
        provideRouter([]),
        { provide: ApiService, useValue: apiStub },
        { provide: LiveService, useValue: liveStub },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(AnalyzerComponent);
    component = fixture.componentInstance;
  });

  it('should run the synchronous REST fallback and load the analysis', () => {
    apiStub.inventory.mockReturnValue(
      of({
        analysis,
        resource_count: 2,
        script_count: 1,
        iframe_count: 0,
        stylesheet_count: 1,
        preconnect_count: 0,
      }),
    );

    component.target = 'example.com';
    component.analyze();

    expect(apiStub.inventory).toHaveBeenCalledWith('example.com');
    expect(component.analysis?.id).toBe(7);
    expect(component.loading).toBe(false);
    expect(component.terminalLines.some((line: string) => line.includes('START REST'))).toBe(true);
  });

  it('should consume live xwa-sdk events and load the persisted analysis', () => {
    apiStub.getAnalysis.mockReturnValue(of(analysis));
    liveStub.connect.mockReturnValue(
      of(
        {
          seq: 1,
          type: 'analysis_started',
          tool: 'musha',
          analysis_id: '7',
          ts: '2026-09-12T10:00:00Z',
          payload: { target: 'example.com' },
        },
        {
          seq: 2,
          type: 'analysis_progress',
          tool: 'musha',
          analysis_id: '7',
          ts: '2026-09-12T10:00:01Z',
          payload: { page: 'https://example.com/', title: 'Example' },
        },
        {
          seq: 3,
          type: 'item_found',
          tool: 'musha',
          analysis_id: '7',
          ts: '2026-09-12T10:00:02Z',
          payload: { kind: 'script', url: 'https://cdn.example.com/a.js', provider: 'Example CDN' },
        },
        {
          seq: 4,
          type: 'analysis_completed',
          tool: 'musha',
          analysis_id: '7',
          ts: '2026-09-12T10:00:03Z',
          payload: { resource_count: 1 },
        },
      ),
    );

    component.target = 'example.com';
    component.runLive();

    expect(liveStub.connect).toHaveBeenCalledWith('ws://test/api/content/live?target=example.com');
    expect(component.terminalLines.some((line: string) => line.includes('PAGE'))).toBe(true);
    expect(
      component.terminalLines.some((line: string) => line.includes('+ SCRIPT Example CDN')),
    ).toBe(true);
    expect(component.analysis?.id).toBe(7);
    expect(component.liveRunning).toBe(false);
    expect(component.phaseState.inventory).toBe('done');
  });

  it('should surface analysis_error events inline (top-level xwa-sdk Error payload)', () => {
    liveStub.connect.mockReturnValue(
      of({
        seq: 2,
        type: 'analysis_error',
        tool: 'musha',
        analysis_id: '7',
        ts: '2026-09-12T10:00:00Z',
        payload: { code: 'TARGET_ERROR', message: 'connection refused', retryable: true },
      }),
    );

    component.target = 'bad.example';
    component.runLive();

    expect(component.error).toContain('connection refused');
    expect(component.liveRunning).toBe(false);
  });

  it('should also tolerate a nested REST-style error payload', () => {
    liveStub.connect.mockReturnValue(
      of({
        seq: 2,
        type: 'analysis_error',
        tool: 'musha',
        analysis_id: '7',
        ts: '2026-09-12T10:00:00Z',
        payload: { error: { code: 'TARGET_ERROR', message: 'nested failure' } },
      }),
    );

    component.target = 'bad.example';
    component.runLive();

    expect(component.error).toContain('nested failure');
  });
});
