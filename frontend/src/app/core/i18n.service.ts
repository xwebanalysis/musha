import { Injectable, signal } from '@angular/core';

export type Locale = 'en' | 'es';

const TRANSLATIONS: Record<Locale, Record<string, string>> = {
  en: {
    'app.tagline': 'XWA - MODULE',
    'nav.analyzer': 'ANALYZER',
    'nav.history': 'HISTORY',
    'nav.exports': 'EXPORTS',
    'dashboard.title': 'CONTENT ANALYSIS',
    'dashboard.subtitle': 'THIRD-PARTY RESOURCE INVENTORY / DOM ANALYSIS',
    'target.label': 'TARGET',
    'target.placeholder': 'https://example.com',
    'action.analyze': 'ANALYZE',
    'action.live': 'LIVE STREAM',
    'action.cancel': 'CANCEL',
    'action.analyzing': 'ANALYZING...',
    'action.delete': 'DELETE',
    'action.delete_all': 'DELETE ALL',
    'action.back': 'BACK',
    'error.backend': 'FAILED TO REACH THE BACKEND',
    'terminal.title': 'LIVE LOG',
    'terminal.empty': '[ NO EVENTS YET ]',
    'phase.connect': 'CONNECT',
    'phase.fetch': 'FETCH',
    'phase.inventory': 'INVENTORY',
    'phase.complete': 'COMPLETE',
    'metric.resources': 'RESOURCES',
    'metric.scripts': 'SCRIPTS',
    'metric.stylesheets': 'STYLES',
    'metric.iframes': 'IFRAMES',
    'history.title': 'HISTORY',
    'history.subtitle': 'RECENT ANALYSES',
    'history.empty': '[ NO ANALYSES YET ]',
    'detail.loading': '[ LOADING... ]',
    'detail.analysis': 'ANALYSIS',
    'detail.scripts': 'SCRIPTS',
    'detail.stylesheets': 'STYLESHEETS',
    'detail.iframes': 'IFRAMES',
    'detail.preconnects': 'PRECONNECTS',
    'detail.other': 'OTHER RESOURCES',
    'detail.no_resources': '[ NO RESOURCES ]',
    'exports.title': 'EXPORTS',
    'exports.subtitle': 'SERVER-SIDE AND CLIENT-SIDE DOWNLOADS',
    'exports.empty': '[ NO ANALYSES YET ]',
    'exports.server_json': 'SERVER JSON',
    'exports.server_csv': 'SERVER CSV',
    'exports.client_json': 'CLIENT JSON',
    'exports.client_pdf': 'CLIENT PDF',
  },
  es: {
    'app.tagline': 'XWA - MODULO',
    'nav.analyzer': 'ANALIZADOR',
    'nav.history': 'HISTORIAL',
    'nav.exports': 'EXPORTAR',
    'dashboard.title': 'ANALISIS DE CONTENIDO',
    'dashboard.subtitle': 'INVENTARIO DE RECURSOS DE TERCEROS / ANALISIS DOM',
    'target.label': 'OBJETIVO',
    'target.placeholder': 'https://ejemplo.com',
    'action.analyze': 'ANALIZAR',
    'action.live': 'STREAM EN VIVO',
    'action.cancel': 'CANCELAR',
    'action.analyzing': 'ANALIZANDO...',
    'action.delete': 'BORRAR',
    'action.delete_all': 'BORRAR TODO',
    'action.back': 'VOLVER',
    'error.backend': 'NO SE PUDO ALCANZAR EL BACKEND',
    'terminal.title': 'LOG EN VIVO',
    'terminal.empty': '[ SIN EVENTOS TODAVIA ]',
    'phase.connect': 'CONEXION',
    'phase.fetch': 'DESCARGA',
    'phase.inventory': 'INVENTARIO',
    'phase.complete': 'COMPLETO',
    'metric.resources': 'RECURSOS',
    'metric.scripts': 'SCRIPTS',
    'metric.stylesheets': 'ESTILOS',
    'metric.iframes': 'IFRAMES',
    'history.title': 'HISTORIAL',
    'history.subtitle': 'ANALISIS RECIENTES',
    'history.empty': '[ SIN ANALISIS TODAVIA ]',
    'detail.loading': '[ CARGANDO... ]',
    'detail.analysis': 'ANALISIS',
    'detail.scripts': 'SCRIPTS',
    'detail.stylesheets': 'HOJAS DE ESTILO',
    'detail.iframes': 'IFRAMES',
    'detail.preconnects': 'PRECONEXIONES',
    'detail.other': 'OTROS RECURSOS',
    'detail.no_resources': '[ SIN RECURSOS ]',
    'exports.title': 'EXPORTAR',
    'exports.subtitle': 'DESCARGAS DEL SERVIDOR Y DEL CLIENTE',
    'exports.empty': '[ SIN ANALISIS TODAVIA ]',
    'exports.server_json': 'JSON SERVIDOR',
    'exports.server_csv': 'CSV SERVIDOR',
    'exports.client_json': 'JSON CLIENTE',
    'exports.client_pdf': 'PDF CLIENTE',
  },
};

@Injectable({ providedIn: 'root' })
export class I18nService {
  private readonly storageKey = 'musha-locale';
  readonly locale = signal<Locale>(this.readStoredLocale());

  t(key: string): string {
    return TRANSLATIONS[this.locale()][key] ?? key;
  }

  toggle(): void {
    this.setLocale(this.locale() === 'en' ? 'es' : 'en');
  }

  setLocale(locale: Locale): void {
    this.locale.set(locale);
    localStorage.setItem(this.storageKey, locale);
  }

  private readStoredLocale(): Locale {
    const stored = localStorage.getItem(this.storageKey);
    return stored === 'es' ? 'es' : 'en';
  }
}
