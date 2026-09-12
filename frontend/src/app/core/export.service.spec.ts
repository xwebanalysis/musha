import { ContentAnalysis } from './api.service';
import { analysisToCsv } from './export.service';

const analysis = {
  id: 4,
  target: 'https://example.com',
  status: 'COMPLETED',
  analysis_type: 'content_scan',
  created_at: '2026-09-12T10:00:00',
  started_at: null,
  finished_at: null,
  error_message: null,
  page_title: 'Example, Inc.',
  resources: [
    {
      id: 1,
      resource_type: 'script',
      url: 'https://cdn.example.com/a.js',
      host: 'cdn.example.com',
      integrity: 'sha384-abc',
      crossorigin: 'anonymous',
      async_attr: true,
      defer_attr: false,
      provider: 'Example CDN',
      category: 'cdn',
    },
    {
      id: 2,
      resource_type: 'iframe',
      url: 'https://video.example.com/embed',
      host: 'video.example.com',
      integrity: null,
      crossorigin: null,
      async_attr: false,
      defer_attr: false,
      provider: null,
      category: null,
    },
  ],
} as ContentAnalysis;

describe('analysisToCsv', () => {
  it('should emit a header and one row per resource', () => {
    const lines = analysisToCsv(analysis).split('\n');
    expect(lines).toHaveLength(3);
    expect(lines[0]).toContain('record_type,analysis_id,target,status,page_title');
    expect(lines[1]).toContain('resource,4,https://example.com,COMPLETED,"Example, Inc."');
    expect(lines[1]).toContain('script,https://cdn.example.com/a.js,cdn.example.com,sha384-abc');
    expect(lines[1]).toContain(',1,0,Example CDN,cdn');
    expect(lines[2]).toContain('iframe,https://video.example.com/embed');
  });

  it('should emit a summary row for analyses without resources', () => {
    const lines = analysisToCsv({ ...analysis, resources: [] }).split('\n');
    expect(lines).toHaveLength(2);
    expect(lines[1]).toContain('analysis,4,https://example.com,COMPLETED');
  });
});
