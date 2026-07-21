import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, map } from 'rxjs';

export let API = 'http://localhost:8000';

export function setApiBase(url: string | undefined | null): void {
  if (url) API = url.replace(/\/+$/, '');
}

export type Rating = 'pending' | 'correct' | 'incorrect';
export type Kind = 'word' | 'line';
export type ImportState = 'queued' | 'processing' | 'done' | 'failed';
export type Mode = 'auto' | 'word' | 'line';
export type Language = 'auto' | 'english' | 'spanish' | 'catalan' | 'chinese' | 'japanese';

export interface CorrectResponse { corrected: string; language: string; }
export interface OcrLine { box: number[]; text: string; }
export interface OcrResult { width: number; height: number; lines: OcrLine[]; text: string; }

export interface GuessResponse { guess: string; confidence: number; kind: Kind; engine: string; }
export interface SampleBody {
  image: string;
  rating: Rating; text: string; engine_guess: string | null;
}
export interface StatsResponse { total: number; by_rating: Record<string, number>; }
export interface ImportJob {
  id: number;
  filename: string;
  state: ImportState;
  pages_total: number;
  pages_done: number;
  lines: number;
  error: string | null;
}
export interface Sample {
  id: number; image_path: string; text: string; language: string;
  rating: Rating; engine_guess: string | null; created_at: string;
}
export interface Metric { cer: number; wer: number; }
export interface EpochStat { epoch: number; cer: number; wer: number; }
export interface ModelInfo {
  id: string; name: string; detail: string; engine: string;
  available: boolean; source: string; best_for: 'words' | 'lines' | null;
  metrics: { words: Metric | null; lines: Metric | null };
  meta: { epoch?: number; cer?: number; wer?: number } | null;
  history: EpochStat[] | null;
}

@Injectable({ providedIn: 'root' })
export class LabelService {
  private http = inject(HttpClient);

  detect(image: string): Observable<{ kind: Kind }> {
    return this.http.post<{ kind: Kind }>(`${API}/label/detect`, { image });
  }
  guess(image: string, mode: Mode = 'auto'): Observable<GuessResponse> {
    return this.http.post<GuessResponse>(`${API}/label/guess`, { image, mode });
  }
  correct(text: string, language: Language, kind: Kind): Observable<CorrectResponse> {
    return this.http.post<CorrectResponse>(`${API}/label/correct`, { text, language, kind });
  }
  sample(body: SampleBody): Observable<{ id: number; image_path: string }> {
    return this.http.post<{ id: number; image_path: string }>(`${API}/label/sample`, body);
  }
  stats(): Observable<StatsResponse> {
    return this.http.get<StatsResponse>(`${API}/label/stats`);
  }
  listSamples(rating?: Rating): Observable<Sample[]> {
    const q = rating ? `?rating=${rating}&limit=100000` : '';
    return this.http.get<Sample[]>(`${API}/label/samples${q}`);
  }
  listPending(): Observable<Sample[]> {
    return this.http.get<Sample[]>(`${API}/label/samples?rating=pending&order=confidence&limit=100000`);
  }
  pageSamples(opts: {
    rating?: Rating; q?: string; limit: number; offset: number;
  }): Observable<Sample[]> {
    const p = new URLSearchParams({ limit: String(opts.limit), offset: String(opts.offset) });
    if (opts.rating) p.set('rating', opts.rating);
    if (opts.q) p.set('q', opts.q);
    return this.http.get<Sample[]>(`${API}/label/samples?${p.toString()}`);
  }
  countSamples(opts: { rating?: Rating; q?: string }): Observable<number> {
    const p = new URLSearchParams();
    if (opts.rating) p.set('rating', opts.rating);
    if (opts.q) p.set('q', opts.q);
    const qs = p.toString();
    return this.http
      .get<{ count: number }>(`${API}/label/samples/count${qs ? '?' + qs : ''}`)
      .pipe(map((r) => r.count));
  }
  importFiles(files: File[]): Observable<{ jobs: ImportJob[] }> {
    const form = new FormData();
    for (const f of files) form.append('files', f);
    return this.http.post<{ jobs: ImportJob[] }>(`${API}/import`, form);
  }
  importStatus(): Observable<ImportJob[]> {
    return this.http.get<ImportJob[]>(`${API}/import/status`);
  }
  imageUrl(id: number): string {
    return `${API}/label/image/${id}`;
  }
  updateSample(id: number, changes: { text?: string; rating?: Rating }): Observable<Sample> {
    return this.http.patch<Sample>(`${API}/label/sample/${id}`, changes);
  }
  deleteSample(id: number): Observable<{ deleted: number }> {
    return this.http.delete<{ deleted: number }>(`${API}/label/sample/${id}`);
  }
  models(): Observable<ModelInfo[]> {
    return this.http.get<ModelInfo[]>(`${API}/models`);
  }
  exportLabels(): Observable<Blob> {
    return this.http.get(`${API}/label/export`, { responseType: 'blob' });
  }
  importLabels(file: File): Observable<{ imported: number }> {
    const form = new FormData();
    form.append('file', file);
    return this.http.post<{ imported: number }>(`${API}/label/import`, form);
  }
  recognizeImage(image: string): Observable<OcrResult> {
    return this.http.post<OcrResult>(`${API}/ocr/recognize`, { image });
  }
  correctLines(lines: OcrLine[], language: Language): Observable<{ lines: OcrLine[] }> {
    return this.http.post<{ lines: OcrLine[] }>(`${API}/ocr/correct`, { lines, language });
  }
  saveOcr(
    image: string, language: Language, lines: { box: number[]; text: string; guess: string | null }[],
  ): Observable<{ saved: number }> {
    return this.http.post<{ saved: number }>(`${API}/ocr/save`, { image, language, lines });
  }
  exportPdf(image: string, width: number, height: number, lines: OcrLine[]): Observable<Blob> {
    return this.http.post(
      `${API}/ocr/pdf`,
      { image, width, height, lines },
      { responseType: 'blob' },
    );
  }
}
