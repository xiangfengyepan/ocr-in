import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { Data } from './data';
import { API } from '../core/label.service';

describe('Data', () => {
  it('loads samples and renders an editable row', async () => {
    await TestBed.configureTestingModule({
      imports: [Data],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();

    const fixture = TestBed.createComponent(Data);
    fixture.detectChanges(); // ngOnInit -> GET /label/samples

    const httpMock = TestBed.inject(HttpTestingController);
    const req = httpMock.expectOne(`${API}/label/samples`);
    expect(req.request.method).toBe('GET');
    req.flush([
      {
        id: 1, image_path: 'english/1.png', text: 'hi', language: 'english',
        rating: 'correct', engine_guess: 'hi', created_at: '',
      },
    ]);
    fixture.detectChanges();

    const el: HTMLElement = fixture.nativeElement;
    expect(el.textContent).toContain('Labeled data');
    expect(el.querySelector('input')).toBeTruthy();
    expect(el.querySelector('img')).toBeTruthy();
    // no explicit Save button — edits auto-save
    expect(el.textContent).not.toContain('Save');
    httpMock.verify();
  });

  it('auto-saves immediately when the rating is toggled', async () => {
    await TestBed.configureTestingModule({
      imports: [Data],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();

    const fixture = TestBed.createComponent(Data);
    fixture.detectChanges();
    const httpMock = TestBed.inject(HttpTestingController);
    httpMock.expectOne(`${API}/label/samples`).flush([
      {
        id: 1, image_path: 'english/1.png', text: 'hi', language: 'english',
        rating: 'correct', engine_guess: 'hi', created_at: '',
      },
    ]);
    fixture.detectChanges();

    const sample = fixture.componentInstance.samples()[0];
    fixture.componentInstance.setRating(sample, 'incorrect');

    const patch = httpMock.expectOne(`${API}/label/sample/1`);
    expect(patch.request.method).toBe('PATCH');
    expect(patch.request.body.rating).toBe('incorrect');
    patch.flush({ ...sample, rating: 'incorrect' });
    httpMock.verify();
  });
});
