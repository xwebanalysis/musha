import { parseLiveEvent } from './live.service';

describe('parseLiveEvent', () => {
  it('should parse a well-formed xwa-sdk Event envelope', () => {
    const event = parseLiveEvent(
      JSON.stringify({
        seq: 3,
        type: 'item_found',
        tool: 'musha',
        analysis_id: '42',
        ts: '2026-09-12T10:00:02+00:00',
        payload: { kind: 'script', url: 'https://cdn.example.com/a.js', provider: 'Example CDN' },
      }),
    );

    expect(event).toEqual({
      seq: 3,
      type: 'item_found',
      tool: 'musha',
      analysis_id: '42',
      ts: '2026-09-12T10:00:02+00:00',
      payload: { kind: 'script', url: 'https://cdn.example.com/a.js', provider: 'Example CDN' },
    });
  });

  it('should reject malformed JSON frames', () => {
    expect(parseLiveEvent('not-json')).toBeNull();
    expect(parseLiveEvent(42)).toBeNull();
    expect(parseLiveEvent(null)).toBeNull();
  });

  it('should reject envelopes without seq, type or analysis_id', () => {
    expect(parseLiveEvent(JSON.stringify({ type: 'analysis_started' }))).toBeNull();
    expect(parseLiveEvent(JSON.stringify({ seq: 1, analysis_id: '1' }))).toBeNull();
    expect(parseLiveEvent(JSON.stringify({ seq: 1, type: 'analysis_started' }))).toBeNull();
  });

  it('should default optional fields and keep a null payload', () => {
    const event = parseLiveEvent(
      JSON.stringify({ seq: 1, type: 'analysis_started', analysis_id: '7' }),
    );
    expect(event?.tool).toBe('');
    expect(event?.ts).toBe('');
    expect(event?.payload).toBeNull();
  });
});
