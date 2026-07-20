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
});
