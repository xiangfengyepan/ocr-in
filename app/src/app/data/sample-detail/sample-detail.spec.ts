import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { SampleDetail } from './sample-detail';
import { API, Sample } from '../../core/label.service';

describe('SampleDetail', () => {
  it('shows guess + correction and auto-saves on rating change', async () => {
    const sample: Sample = {
      id: 5, image_path: 'english/5.png', text: 'gues', language: 'english',
      rating: 'incorrect', engine_guess: 'gues', created_at: '',
    };
    await TestBed.configureTestingModule({
      imports: [SampleDetail],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: MAT_DIALOG_DATA, useValue: sample },
        { provide: MatDialogRef, useValue: { close: () => {} } },
      ],
    }).compileComponents();

    const fixture = TestBed.createComponent(SampleDetail);
    fixture.detectChanges();
    const el: HTMLElement = fixture.nativeElement;
    expect(el.textContent).toContain('Model guess');
    expect(el.textContent).toContain('Correction');

    fixture.componentInstance.setRating('correct');
    const http = TestBed.inject(HttpTestingController);
    const patch = http.expectOne(`${API}/label/sample/5`);
    expect(patch.request.method).toBe('PATCH');
    expect(patch.request.body.rating).toBe('correct');
    patch.flush({ ...sample, rating: 'correct' });
    http.verify();
  });
});
