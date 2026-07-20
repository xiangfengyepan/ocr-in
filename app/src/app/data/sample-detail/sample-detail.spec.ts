import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { of } from 'rxjs';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { SampleDetail } from './sample-detail';
import { API, Sample } from '../../core/label.service';

const SAMPLE: Sample = {
  id: 5, image_path: 'english/5.png', text: 'guess', language: 'english',
  rating: 'incorrect', engine_guess: 'gues', created_at: '',
};

function setup() {
  TestBed.configureTestingModule({
    imports: [SampleDetail],
    providers: [
      provideHttpClient(),
      provideHttpClientTesting(),
      { provide: MAT_DIALOG_DATA, useValue: { ...SAMPLE } },
      { provide: MatDialogRef, useValue: { close: () => undefined } },
    ],
  });
  const fixture = TestBed.createComponent(SampleDetail);
  fixture.detectChanges();
  return fixture;
}

describe('SampleDetail', () => {
  it('renders the label read-only (guess, label, rating) and never PATCHes', () => {
    const fixture = setup();
    const el: HTMLElement = fixture.nativeElement;
    expect(el.textContent).toContain('Model guess');
    expect(el.textContent).toContain('Label');
    expect(el.textContent).toContain('guess');
    expect(el.textContent).toContain('Read-only');
    // no editable inputs / toggles present
    expect(el.querySelector('input')).toBeNull();
    expect(el.querySelector('mat-button-toggle')).toBeNull();

    const http = TestBed.inject(HttpTestingController);
    http.expectNone((r) => r.method === 'PATCH');
    http.verify();
  });

  it('deletes on confirm and closes', () => {
    const fixture = setup();
    // MatDialogModule (imported by the component) shadows a DI stub, so set the
    // confirm dialog directly to auto-confirm.
    (fixture.componentInstance as unknown as { dialog: unknown }).dialog = {
      open: () => ({ afterClosed: () => of(true) }),
    };
    fixture.componentInstance.remove();
    const http = TestBed.inject(HttpTestingController);
    const del = http.expectOne(`${API}/label/sample/5`);
    expect(del.request.method).toBe('DELETE');
    del.flush({ deleted: 5 });
    http.verify();
  });
});
