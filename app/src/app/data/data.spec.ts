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
    httpMock.verify();
  });
});
