import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

const API = 'http://localhost:8000';

export interface GuessResponse { guess: string; confidence: number; }
export interface SampleBody {
  image: string; language: string;
  rating: 'correct' | 'partial' | 'wrong'; text: string; engine_guess: string | null;
}
export interface StatsResponse { total: number; by_rating: Record<string, number>; }

@Injectable({ providedIn: 'root' })
export class LabelService {
  private http = inject(HttpClient);
  guess(image: string, language: string): Observable<GuessResponse> {
    return this.http.post<GuessResponse>(`${API}/label/guess`, { image, language });
  }
  sample(body: SampleBody): Observable<{ id: number; image_path: string }> {
    return this.http.post<{ id: number; image_path: string }>(`${API}/label/sample`, body);
  }
  stats(): Observable<StatsResponse> {
    return this.http.get<StatsResponse>(`${API}/label/stats`);
  }
}
