import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { Ocr } from './ocr';
import { API } from '../core/label.service';

describe('Ocr', () => {
  it('recognizes an uploaded image and stores the result', async () => {
    await TestBed.configureTestingModule({
      imports: [Ocr],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();

    const fixture = TestBed.createComponent(Ocr);
    fixture.detectChanges();
    const c = fixture.componentInstance;
    c.image.set('data:image/png;base64,AAAA');
    c.recognize();

    const http = TestBed.inject(HttpTestingController);
    const req = http.expectOne(`${API}/ocr/recognize`);
    expect(req.request.method).toBe('POST');
    req.flush({ width: 100, height: 50, lines: [{ box: [0, 0, 10, 10], text: 'hi' }], text: 'hi' });

    expect(c.result()?.text).toBe('hi');
    expect(c.result()?.lines.length).toBe(1);
    http.verify();
  });

  it('edits a line and rebuilds the joined text', async () => {
    await TestBed.configureTestingModule({
      imports: [Ocr],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();

    const c = TestBed.createComponent(Ocr).componentInstance;
    c.result.set({
      width: 100,
      height: 50,
      lines: [
        { box: [0, 0, 10, 10], text: 'foo' },
        { box: [0, 10, 10, 20], text: 'bar' },
      ],
      text: 'foo\nbar',
    });

    c.editLine(0, { target: { innerText: 'FOO' } } as unknown as Event);

    expect(c.result()?.lines[0].text).toBe('FOO');
    expect(c.result()?.text).toBe('FOO\nbar');
  });

  it('exports the edited lines to a searchable PDF', async () => {
    await TestBed.configureTestingModule({
      imports: [Ocr],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();

    URL.createObjectURL = () => 'blob:mock';
    URL.revokeObjectURL = () => undefined;
    HTMLAnchorElement.prototype.click = () => undefined;

    const c = TestBed.createComponent(Ocr).componentInstance;
    c.image.set('data:image/png;base64,AAAA');
    c.result.set({
      width: 100,
      height: 50,
      lines: [{ box: [0, 0, 10, 10], text: 'hi' }],
      text: 'hi',
    });

    c.exportPdf();

    const http = TestBed.inject(HttpTestingController);
    const req = http.expectOne(`${API}/ocr/pdf`);
    expect(req.request.method).toBe('POST');
    expect(req.request.body.lines[0].text).toBe('hi');
    expect(req.request.responseType).toBe('blob');
    req.flush(new Blob(['%PDF-1.7'], { type: 'application/pdf' }));
    http.verify();
  });

  it('saves recognized lines to the data store with the raw guess', async () => {
    await TestBed.configureTestingModule({
      imports: [Ocr],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();

    const c = TestBed.createComponent(Ocr).componentInstance;
    c.image.set('data:image/png;base64,AAAA');
    c.result.set({
      width: 100,
      height: 50,
      lines: [{ box: [0, 0, 10, 10], text: 'helo' }],
      text: 'helo',
    });
    c.corrected.set([{ box: [0, 0, 10, 10], text: 'hello' }]);
    c.showCorrected.set(true);

    c.saveToData();

    const http = TestBed.inject(HttpTestingController);
    const req = http.expectOne(`${API}/ocr/save`);
    expect(req.request.method).toBe('POST');
    expect(req.request.body.lines[0].text).toBe('hello');
    expect(req.request.body.lines[0].guess).toBe('helo');
    req.flush({ saved: 1 });
    http.verify();
  });

  it('corrects as a separate step and toggles between original and corrected', async () => {
    await TestBed.configureTestingModule({
      imports: [Ocr],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();

    const c = TestBed.createComponent(Ocr).componentInstance;
    c.result.set({
      width: 100,
      height: 50,
      lines: [{ box: [0, 0, 10, 10], text: 'helo wrld' }],
      text: 'helo wrld',
    });

    // turning it on fetches corrections once
    c.toggleCorrected(true);
    const http = TestBed.inject(HttpTestingController);
    const req = http.expectOne(`${API}/ocr/correct`);
    expect(req.request.method).toBe('POST');
    expect(req.request.body.lines[0].text).toBe('helo wrld');
    req.flush({ lines: [{ box: [0, 0, 10, 10], text: 'hello world' }] });

    expect(c.showCorrected()).toBe(true);
    expect(c.displayText()).toBe('hello world');

    // toggling off shows the original without another request
    c.toggleCorrected(false);
    expect(c.displayText()).toBe('helo wrld');

    // toggling back on reuses the cached correction (no new request)
    c.toggleCorrected(true);
    expect(c.displayText()).toBe('hello world');
    http.verify();
  });
});
