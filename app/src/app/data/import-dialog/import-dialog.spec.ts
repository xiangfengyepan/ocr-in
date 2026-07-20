import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { MatDialogRef } from '@angular/material/dialog';
import { API, ImportJob } from '../../core/label.service';
import { ImportDialog } from './import-dialog';

function setup() {
  TestBed.configureTestingModule({
    imports: [ImportDialog],
    providers: [
      provideHttpClient(),
      provideHttpClientTesting(),
      { provide: MatDialogRef, useValue: { close: () => undefined } },
    ],
  });
  const fixture = TestBed.createComponent(ImportDialog);
  const http = TestBed.inject(HttpTestingController);
  return { c: fixture.componentInstance, http };
}

describe('ImportDialog', () => {
  it('processes selected files, switches to status, and polls only this session', () => {
    const { c, http } = setup();
    c.files.set([new File(['x'], 'note.pdf', { type: 'application/pdf' })]);

    c.process();
    const queued: ImportJob[] = [
      { id: 10, filename: 'note.pdf', state: 'queued', pages_total: 3, pages_done: 0, lines: 0, error: null },
    ];
    const req = http.expectOne((r) => r.url.endsWith('/import') && r.method === 'POST');
    req.flush({ jobs: queued });
    expect(c.mode()).toBe('status');

    // immediate poll; a foreign job (id 99) is filtered out, ours (id 10) kept
    const done: ImportJob[] = [
      { id: 10, filename: 'note.pdf', state: 'done', pages_total: 3, pages_done: 3, lines: 42, error: null },
      { id: 99, filename: 'other.pdf', state: 'processing', pages_total: 1, pages_done: 0, lines: 0, error: null },
    ];
    http.expectOne((r) => r.url.includes('/import/status')).flush(done);
    expect(c.jobs().map((j) => j.id)).toEqual([10]);
    expect(c.allDone()).toBe(true);
    http.verify();
  });

  it('does not process when no files are selected', () => {
    const { c, http } = setup();
    c.process();
    http.expectNone((r) => r.url.endsWith('/import'));
    expect(c.mode()).toBe('select');
    http.verify();
  });
});
