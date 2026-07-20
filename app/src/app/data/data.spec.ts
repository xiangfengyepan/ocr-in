import { vi } from 'vitest';
import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideRouter } from '@angular/router';
import { of } from 'rxjs';
import { MatDialog } from '@angular/material/dialog';
import { Data } from './data';
import { Sample } from '../core/label.service';

const ROWS: Sample[] = [
  { id: 1, image_path: 'english/1.png', text: 'hello', language: 'english', rating: 'correct', engine_guess: 'helo', created_at: '' },
  { id: 2, image_path: 'english/2.png', text: 'world', language: 'english', rating: 'incorrect', engine_guess: 'wrld', created_at: '' },
];

const STATS = { total: 2, by_rating: { pending: 5, correct: 1, incorrect: 1 } };

function flushPage(http: HttpTestingController, rows: Sample[] = ROWS, total = 42) {
  http.expectOne((r) => r.url.includes('/label/samples/count')).flush({ count: total });
  http.expectOne((r) => r.url.includes('/label/samples') && !r.url.includes('/count')).flush(rows);
}

function flushStats(http: HttpTestingController) {
  http.expectOne((r) => r.url.includes('/label/stats')).flush(STATS);
}

function setup(dialogStub?: unknown) {
  TestBed.configureTestingModule({
    imports: [Data],
    providers: [
      provideHttpClient(),
      provideHttpClientTesting(),
      provideRouter([]),
      ...(dialogStub ? [{ provide: MatDialog, useValue: dialogStub }] : []),
    ],
  });
  const fixture = TestBed.createComponent(Data);
  fixture.detectChanges();
  const http = TestBed.inject(HttpTestingController);
  flushPage(http);
  flushStats(http);
  fixture.detectChanges();
  return { fixture, http };
}

describe('Data', () => {
  it('loads a page of samples and shows the total', () => {
    const { fixture, http } = setup();
    const c = fixture.componentInstance;
    expect(c.samples().length).toBe(2);
    expect(c.total()).toBe(42);
    const el: HTMLElement = fixture.nativeElement;
    expect(el.textContent).toContain('42 total');
    http.verify();
  });

  it('feeds the pending count into the fast-review label', () => {
    const { fixture, http } = setup();
    expect(fixture.componentInstance.pendingCount()).toBe(5);
    expect((fixture.nativeElement as HTMLElement).textContent).toContain('Fast review — 5 unlabeled');
    http.verify();
  });

  it('requests rating=pending for the Unlabeled filter and resets to page 0', () => {
    const { fixture, http } = setup();
    const c = fixture.componentInstance;
    c.pageIndex.set(3);
    c.setFilter('pending');
    expect(c.pageIndex()).toBe(0);
    http.expectOne((r) => r.url.includes('/label/samples/count') && r.url.includes('rating=pending')).flush({ count: 5 });
    const page = http.expectOne((r) => r.url.includes('/label/samples') && !r.url.includes('/count') && r.url.includes('rating=pending'));
    expect(page.request.method).toBe('GET');
    page.flush(ROWS);
    http.verify();
  });

  it('debounces text search into a q= request', () => {
    const { fixture, http } = setup();
    vi.useFakeTimers();
    try {
      fixture.componentInstance.onQuery('hell');
      vi.advanceTimersByTime(300);
    } finally {
      vi.useRealTimers();
    }
    http.expectOne((r) => r.url.includes('/label/samples/count') && r.url.includes('q=hell')).flush({ count: 1 });
    http.expectOne((r) => r.url.includes('/label/samples') && !r.url.includes('/count') && r.url.includes('q=hell')).flush([ROWS[0]]);
    http.verify();
  });

  it('paginates via the paginator event', () => {
    const { fixture, http } = setup();
    const c = fixture.componentInstance;
    c.onPage({ pageIndex: 2, pageSize: 10, length: 42 });
    expect(c.pageIndex()).toBe(2);
    expect(c.pageSize()).toBe(10);
    const page = http.expectOne((r) => r.url.includes('/label/samples') && !r.url.includes('/count') && r.url.includes('offset=20') && r.url.includes('limit=10'));
    page.flush(ROWS);
    http.expectOne((r) => r.url.includes('/label/samples/count')).flush({ count: 42 });
    http.verify();
  });

  it('selects on single click and opens the detail dialog on double click', () => {
    const opened: unknown[] = [];
    // afterClosed emits nothing so the dialog-close reload does not fire here
    const dialog = { open: (...a: unknown[]) => { opened.push(a); return { afterClosed: () => of() }; } };
    const { fixture, http } = setup(dialog);
    const c = fixture.componentInstance;
    c.select(ROWS[0]);
    expect(c.selectedId()).toBe(1);
    c.openDetail(ROWS[0]);
    expect(opened.length).toBe(1);
    http.verify();
  });

  it('deletes a row after confirmation and reloads', () => {
    const dialog = { open: () => ({ afterClosed: () => of(true) }) };
    const { fixture, http } = setup(dialog);
    fixture.componentInstance.deleteRow(ROWS[0], new Event('click'));
    const del = http.expectOne((r) => r.url.includes('/label/sample/1') && r.method === 'DELETE');
    del.flush({ deleted: 1 });
    flushPage(http);
    flushStats(http);
    http.verify();
  });

  it('opens the import dialog and reloads when it closes', () => {
    const dialog = { open: () => ({ afterClosed: () => of(true) }) };
    const { fixture, http } = setup(dialog);
    fixture.componentInstance.openImport();
    flushPage(http);
    flushStats(http);
    http.verify();
  });
});
