import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export const API = 'http://localhost:8000';

export type Rating = 'correct' | 'incorrect';

export interface GuessResponse { guess: string; confidence: number; }
export interface SampleBody {
  image: string;
  rating: Rating; text: string; engine_guess: string | null;
}
export interface StatsResponse { total: number; by_rating: Record<string, number>; }
export interface Sample {
  id: number; image_path: string; text: string; language: string;
  rating: Rating; engine_guess: string | null; created_at: string;
}
export interface Metric { cer: number; wer: number; }
export interface ModelInfo {
  id: string; name: string; detail: string; engine: string;
  available: boolean; source: string; best_for: 'words' | 'lines' | null;
  metrics: { words: Metric | null; lines: Metric | null };
}

@Injectable({ providedIn: 'root' })
export class LabelService {
  private http = inject(HttpClient);

  guess(image: string): Observable<GuessResponse> {
    return this.http.post<GuessResponse>(`${API}/label/guess`, { image });
  }
  sample(body: SampleBody): Observable<{ id: number; image_path: string }> {
    return this.http.post<{ id: number; image_path: string }>(`${API}/label/sample`, body);
  }
  stats(): Observable<StatsResponse> {
    return this.http.get<StatsResponse>(`${API}/label/stats`);
  }
  listSamples(): Observable<Sample[]> {
    return this.http.get<Sample[]>(`${API}/label/samples`);
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
}
