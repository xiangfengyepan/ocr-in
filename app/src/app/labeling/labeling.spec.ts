import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { Labeling } from './labeling';

function setup() {
  TestBed.configureTestingModule({
    imports: [Labeling],
    providers: [provideHttpClient(), provideHttpClientTesting()],
  });
  const fixture = TestBed.createComponent(Labeling);
  fixture.detectChanges();
  const http = TestBed.inject(HttpTestingController);
  return { fixture, http };
}

describe('Labeling', () => {
  it('creates and shows the canvas + Guess button', () => {
    const { fixture } = setup();
    const el: HTMLElement = fixture.nativeElement;
    expect(el.querySelector('canvas')).toBeTruthy();
    expect(el.textContent).toContain('Guess');
    fixture.destroy();
  });

  it('is not GPU-disabled and omits engine (auto) when nothing is training', () => {
    const { fixture, http } = setup();
    const c = fixture.componentInstance;
    expect(c.gpuDisabled()).toBe(false);

    c.doGuess();
    const req = http.expectOne((r) => r.url.includes('/label/guess'));
    expect(req.request.body.engine).toBeUndefined();
    req.flush({ guess: 'hi', confidence: 0.9, kind: 'word', engine: 'trocr' });

    // doGuess refreshes availability afterwards
    http
      .expectOne((r) => r.url.includes('/engines/availability'))
      .flush({ trocr: true, crnn: true, tesseract: true, training: false });

    http.verify();
    fixture.destroy();
  });

  it('disables GPU engines and forces Tesseract while training', () => {
    const { fixture, http } = setup();
    const c = fixture.componentInstance;
    c.availability.set({ trocr: false, crnn: false, tesseract: true, training: true });
    expect(c.gpuDisabled()).toBe(true);

    c.engine.set('crnn');
    c.doGuess();
    const req = http.expectOne((r) => r.url.includes('/label/guess'));
    expect(req.request.body.engine).toBe('tesseract');
    req.flush({ guess: 'hi', confidence: 0.9, kind: 'word', engine: 'tesseract' });

    // still training after the guess: availability refresh keeps the poll alive
    http
      .expectOne((r) => r.url.includes('/engines/availability'))
      .flush({ trocr: false, crnn: false, tesseract: true, training: true });

    http.verify();
    fixture.destroy();
  });
});
