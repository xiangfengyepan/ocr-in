import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { Review } from './review';
import { API, Sample } from '../core/label.service';

function sample(id: number, text: string): Sample {
  return {
    id,
    image_path: `p${id}.png`,
    text,
    language: 'english',
    rating: 'pending',
    engine_guess: null,
    created_at: '2026-01-01',
  };
}

function setup() {
  TestBed.configureTestingModule({
    imports: [Review],
    providers: [provideHttpClient(), provideHttpClientTesting()],
  });
  const fixture = TestBed.createComponent(Review);
  const c = fixture.componentInstance;
  const http = TestBed.inject(HttpTestingController);
  fixture.detectChanges();
  return { c, http };
}

function flushQueue(http: HttpTestingController, samples: Sample[]): void {
  const req = http.expectOne(
    (r) => r.url.includes('/label/samples') && r.url.includes('order=confidence'),
  );
  expect(req.request.method).toBe('GET');
  req.flush(samples);
}

describe('Review', () => {
  it('loads the pending queue on init', () => {
    const { c, http } = setup();
    flushQueue(http, [sample(1, 'foo'), sample(2, 'bar')]);

    expect(c.queue().length).toBe(2);
    expect(c.current()?.id).toBe(1);
    expect(c.loading()).toBe(false);
    http.verify();
  });

  it('marks Correct, PATCHes with rating correct and advances', () => {
    const { c, http } = setup();
    flushQueue(http, [sample(1, 'foo'), sample(2, 'bar')]);

    c.markCorrect();
    const req = http.expectOne(`${API}/label/sample/1`);
    expect(req.request.method).toBe('PATCH');
    expect(req.request.body.rating).toBe('correct');
    req.flush(sample(1, 'foo'));

    expect(c.index()).toBe(1);
    expect(c.current()?.id).toBe(2);
    http.verify();
  });

  it('marks Incorrect, saves edited text and advances', () => {
    const { c, http } = setup();
    flushQueue(http, [sample(1, 'helo'), sample(2, 'bar')]);

    c.openFix();
    c.fixText.set('hello');
    c.saveFix();

    const req = http.expectOne(`${API}/label/sample/1`);
    expect(req.request.method).toBe('PATCH');
    expect(req.request.body.rating).toBe('incorrect');
    expect(req.request.body.text).toBe('hello');
    req.flush(sample(1, 'hello'));

    expect(c.fixing()).toBe(false);
    expect(c.index()).toBe(1);
    http.verify();
  });

  it('has a null current when the queue is empty', () => {
    const { c, http } = setup();
    flushQueue(http, []);

    expect(c.current()).toBeNull();
    expect(c.done()).toBe(true);
    http.verify();
  });
});
