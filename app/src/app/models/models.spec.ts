import { vi } from 'vitest';
import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { Models } from './models';
import { API, TrainJob } from '../core/label.service';

const MODEL: unknown = {
  id: 'crnn-words', name: 'CRNN', detail: 'x', engine: 'crnn', available: true,
  source: 'models/crnn/english', best_for: 'words',
  metrics: { words: { cer: 0.103, wer: 0.24 }, lines: { cer: 0.431, wer: 1 } },
  meta: { epoch: 54, cer: 0.103, wer: 0.24 },
  history: [{ epoch: 1, cer: 0.5, wer: 0.7 }, { epoch: 2, cer: 0.2, wer: 0.4 }],
};

function setup() {
  TestBed.configureTestingModule({
    imports: [Models],
    providers: [provideHttpClient(), provideHttpClientTesting()],
  });
  const fixture = TestBed.createComponent(Models);
  fixture.detectChanges();
  const http = TestBed.inject(HttpTestingController);
  http.expectOne(`${API}/models`).flush([MODEL]);
  http.expectOne((r) => r.url.includes('/train/status')).flush([]);
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

  it('rehydrates in-progress jobs from status on init and resumes polling', () => {
    TestBed.configureTestingModule({
      imports: [Models],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    const fixture = TestBed.createComponent(Models);
    const c = fixture.componentInstance;

    vi.useFakeTimers();
    try {
      fixture.detectChanges();
      const http = TestBed.inject(HttpTestingController);
      http.expectOne(`${API}/models`).flush([MODEL]);
      const active: TrainJob = {
        id: 42, kind: 'line', state: 'training', epoch: 2, epochs_total: 8,
        base_cer: null, base_wer: null, new_cer: null, new_wer: null,
        candidate_path: null, promoted: false, error: null,
      };
      http.expectOne((r) => r.url.includes('/train/status')).flush([active]);
      fixture.detectChanges();

      expect(c.jobs().line?.id).toBe(42);
      expect(c.isActive(c.jobs().line)).toBe(true);

      // polling resumed
      vi.advanceTimersByTime(2000);
      http.expectOne((r) => r.url.includes('/train/status'))
        .flush([{ ...active, state: 'done', epoch: 8 }]);
      fixture.detectChanges();
      expect(c.jobs().line?.state).toBe('done');
      http.verify();
    } finally {
      vi.useRealTimers();
    }
  });

  it('starts training and renders the polled job state', () => {
    const { fixture, http } = setup();
    const c = fixture.componentInstance;

    vi.useFakeTimers();
    try {
      c.train('line');
      const queued: TrainJob = {
        id: 7, kind: 'line', state: 'queued', epoch: 0, epochs_total: 10,
        base_cer: null, base_wer: null, new_cer: null, new_wer: null,
        candidate_path: null, promoted: false, error: null,
      };
      http.expectOne((r) => r.url.endsWith('/train') && r.method === 'POST').flush({ job: queued });
      expect(c.jobs().line?.id).toBe(7);

      const training: TrainJob = { ...queued, state: 'training', epoch: 3 };
      vi.advanceTimersByTime(2000);
      http.expectOne((r) => r.url.includes('/train/status')).flush([training]);
      fixture.detectChanges();

      const el: HTMLElement = fixture.nativeElement;
      expect(el.textContent).toContain('training');
      expect(el.textContent).toContain('3/10');
      expect(c.isActive(c.jobs().line)).toBe(true);
    } finally {
      vi.useRealTimers();
    }
    http.verify();
  });

  it('shows the before/after table on a done job', () => {
    const { fixture, http } = setup();
    const c = fixture.componentInstance;

    vi.useFakeTimers();
    try {
      c.train('word');
      const queued: TrainJob = {
        id: 8, kind: 'word', state: 'queued', epoch: 0, epochs_total: 5,
        base_cer: null, base_wer: null, new_cer: null, new_wer: null,
        candidate_path: null, promoted: false, error: null,
      };
      http.expectOne((r) => r.url.endsWith('/train') && r.method === 'POST').flush({ job: queued });

      const done: TrainJob = {
        ...queued, state: 'done', epoch: 5,
        base_cer: 0.2, base_wer: 0.4, new_cer: 0.1, new_wer: 0.3,
        candidate_path: '/tmp/candidate',
      };
      vi.advanceTimersByTime(2000);
      http.expectOne((r) => r.url.includes('/train/status')).flush([done]);
      fixture.detectChanges();

      expect(c.jobs().word?.state).toBe('done');
      const el: HTMLElement = fixture.nativeElement;
      expect(el.textContent).toContain('20.0%');
      expect(el.textContent).toContain('10.0%');
      expect(el.textContent).toContain('Use this model');

      // polling stops once no job is active
      vi.advanceTimersByTime(4000);
      http.expectNone((r) => r.url.includes('/train/status'));
    } finally {
      vi.useRealTimers();
    }
    http.verify();
  });

  it('promotes a model and reloads the catalog', () => {
    const { fixture, http } = setup();
    const c = fixture.componentInstance;

    c.jobs.set({
      line: null,
      word: {
        id: 8, kind: 'word', state: 'done', epoch: 5, epochs_total: 5,
        base_cer: 0.2, base_wer: 0.4, new_cer: 0.1, new_wer: 0.3,
        candidate_path: '/tmp/candidate', promoted: false, error: null,
      },
    });
    fixture.detectChanges();

    c.promote('word');
    http.expectOne((r) => r.url.endsWith('/train/promote') && r.method === 'POST')
      .flush({ promoted: true, engine: 'crnn', kind: 'word' });
    http.expectOne(`${API}/models`).flush([MODEL]);

    expect(c.jobs().word?.promoted).toBe(true);
    fixture.detectChanges();
    expect((fixture.nativeElement as HTMLElement).textContent).toContain('Promoted');
    http.verify();
  });
});
