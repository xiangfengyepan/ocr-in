import { vi } from 'vitest';
import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { MatDialog } from '@angular/material/dialog';
import { Models } from './models';
import { API } from '../core/label.service';

const MODEL: unknown = {
  id: 'crnn-words', name: 'CRNN', detail: 'x', engine: 'crnn', available: true,
  source: 'models/crnn/english', best_for: 'words',
  metrics: { words: { cer: 0.103, wer: 0.24 }, lines: { cer: 0.431, wer: 1 } },
  meta: { epoch: 54, cer: 0.103, wer: 0.24 },
  history: [{ epoch: 1, cer: 0.5, wer: 0.7 }, { epoch: 2, cer: 0.2, wer: 0.4 }],
};

const PERSONALIZED: unknown[] = [
  {
    id: 'trocr-line-personal', name: 'TrOCR (line) — personalized',
    detail: 'Fine-tuned on your labeled data', engine: 'trocr', available: true,
    source: 'models/trocr/english', best_for: 'lines',
    metrics: { words: null, lines: { cer: 0.05, wer: 0.12 } },
    meta: { epoch: 7, cer: 0.05, wer: 0.12 },
    history: [{ epoch: 1, cer: 0.3, wer: 0.5 }, { epoch: 7, cer: 0.05, wer: 0.12 }],
  },
  {
    id: 'crnn-word-personal', name: 'CRNN (word) — personalized',
    detail: 'Not yet trained — using stock/default', engine: 'crnn', available: false,
    source: 'models/crnn/english', best_for: 'words',
    metrics: { words: null, lines: null }, meta: null, history: null,
  },
];

function setup() {
  TestBed.configureTestingModule({
    imports: [Models],
    providers: [provideHttpClient(), provideHttpClientTesting()],
  });
  const fixture = TestBed.createComponent(Models);
  fixture.detectChanges();
  const http = TestBed.inject(HttpTestingController);
  http.expectOne(`${API}/models`).flush([MODEL]);
  http.expectOne(`${API}/train/models`).flush(PERSONALIZED);
  fixture.detectChanges();
  return { fixture, http };
}

describe('Models', () => {
  it('loads and renders the model table', () => {
    const { fixture, http } = setup();
    const el: HTMLElement = fixture.nativeElement;
    expect(el.textContent).toContain('CRNN');
    expect(el.textContent).toContain('10.3%');
    http.verify();
  });

  it('renders the personalized table and opens the chart on row click', () => {
    const { fixture, http } = setup();
    const dialog = TestBed.inject(MatDialog);
    const openSpy = vi.spyOn(dialog, 'open').mockReturnValue({} as never);
    const el: HTMLElement = fixture.nativeElement;

    expect(el.textContent).toContain('Personalized models');
    expect(el.textContent).toContain('TrOCR (line) — personalized');
    expect(el.textContent).toContain('CRNN (word) — personalized');
    expect(el.textContent).toContain('fine-tuned');
    expect(el.textContent).toContain('stock/default');

    const rows = el.querySelectorAll('.models:last-of-type tbody tr.row');
    expect(rows.length).toBe(2);
    (rows[0] as HTMLElement).click();
    expect(openSpy).toHaveBeenCalled();
    http.verify();
  });
});
