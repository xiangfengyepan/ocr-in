import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { Models } from './models';
import { API } from '../core/label.service';

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
});
