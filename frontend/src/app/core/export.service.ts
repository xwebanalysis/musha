import { Injectable } from '@angular/core';

import { ContentAnalysis } from './api.service';

const CSV_HEADER = [
  'record_type',
  'analysis_id',
  'target',
  'status',
  'page_title',
  'resource_type',
  'url',
  'host',
  'integrity',
  'crossorigin',
  'async',
  'defer',
  'provider',
  'category',
];

/** Build the client-side CSV export for a content analysis. */
export function analysisToCsv(analysis: ContentAnalysis): string {
  const rows: (string | number)[][] = [[...CSV_HEADER]];

  if (analysis.resources.length === 0) {
    rows.push([
      'analysis',
      analysis.id,
      analysis.target,
      analysis.status,
      analysis.page_title ?? '',
      '', '', '', '', '', '', '', '', '',
    ]);
  }

  for (const resource of analysis.resources) {
    rows.push([
      'resource',
      analysis.id,
      analysis.target,
      analysis.status,
      analysis.page_title ?? '',
      resource.resource_type,
      resource.url ?? '',
      resource.host ?? '',
      resource.integrity ?? '',
      resource.crossorigin ?? '',
      resource.async_attr ? 1 : 0,
      resource.defer_attr ? 1 : 0,
      resource.provider ?? '',
      resource.category ?? '',
    ]);
  }

  return rows.map((row) => row.map((cell) => escapeCsv(cell)).join(',')).join('\n');
}

function escapeCsv(value: string | number): string {
  const text = String(value ?? '');
  if (/[",\n]/.test(text)) {
    return `"${text.replace(/"/g, '""')}"`;
  }
  return text;
}

/**
 * Client-side exports: JSON/CSV blobs and a jsPDF report. The PDF dependency is
 * loaded lazily so the initial bundle stays lean and tests never need jsPDF.
 */
@Injectable({ providedIn: 'root' })
export class ExportService {
  downloadJson(analysis: ContentAnalysis): void {
    const blob = new Blob([JSON.stringify(analysis, null, 2)], {
      type: 'application/json;charset=utf-8',
    });
    this.download(blob, `musha-analysis-${analysis.id}.json`);
  }

  downloadCsv(analysis: ContentAnalysis): void {
    this.download(
      new Blob([analysisToCsv(analysis)], { type: 'text/csv;charset=utf-8' }),
      `musha-analysis-${analysis.id}.csv`,
    );
  }

  async downloadPdf(analysis: ContentAnalysis): Promise<void> {
    const { jsPDF } = await import('jspdf');
    const doc = new jsPDF({ unit: 'pt', format: 'a4' });
    const margin = 48;
    let y = margin;

    const line = (text: string, size = 9, style: 'normal' | 'bold' = 'normal', gap = 14) => {
      doc.setFont('courier', style);
      doc.setFontSize(size);
      const wrapped = doc.splitTextToSize(text, 595 - margin * 2) as string[];
      for (const chunk of wrapped) {
        if (y > 800) {
          doc.addPage();
          y = margin;
        }
        doc.text(chunk, margin, y);
        y += gap;
      }
    };

    line('MUSHA / CONTENT & DOM ANALYSIS', 16, 'bold', 20);
    line(`ANALYSIS #${analysis.id}`, 11, 'bold');
    line(`TARGET:   ${analysis.target}`);
    line(`STATUS:   ${analysis.status}`);
    line(`CREATED:  ${analysis.created_at}`);
    line(`TITLE:    ${analysis.page_title ?? 'n/a'}`);
    y += 8;

    line('SUMMARY', 11, 'bold');
    line(`RESOURCES:   ${analysis.resources.length}`);
    line(`SCRIPTS:     ${this.count(analysis, 'script')}`);
    line(`STYLESHEETS: ${this.count(analysis, 'stylesheet')}`);
    line(`IFRAMES:     ${this.count(analysis, 'iframe')}`);
    line(`PRECONNECTS: ${this.count(analysis, 'preconnect')}`);
    y += 8;

    for (const type of ['script', 'stylesheet', 'iframe', 'preconnect', 'other']) {
      const resources =
        type === 'other'
          ? analysis.resources.filter((resource) => !['script', 'stylesheet', 'iframe', 'preconnect'].includes(resource.resource_type))
          : analysis.resources.filter((resource) => resource.resource_type === type);
      if (resources.length === 0) {
        continue;
      }
      line(`${type.toUpperCase()} (${resources.length})`, 11, 'bold');
      for (const resource of resources) {
        const flags = [
          resource.provider ? `provider=${resource.provider}` : '',
          resource.integrity ? 'sri' : '',
          resource.crossorigin ? `crossorigin=${resource.crossorigin}` : '',
          resource.async_attr ? 'async' : '',
          resource.defer_attr ? 'defer' : '',
        ]
          .filter(Boolean)
          .join(' ');
        line(`- ${resource.url ?? '(inline)'}${flags ? `  [${flags}]` : ''}`);
      }
      y += 4;
    }

    doc.save(`musha-analysis-${analysis.id}.pdf`);
  }

  private count(analysis: ContentAnalysis, type: string): number {
    return analysis.resources.filter((resource) => resource.resource_type === type).length;
  }

  private download(blob: Blob, filename: string): void {
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    link.rel = 'noopener';
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  }
}
