import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { of } from 'rxjs';
import { MatDialog } from '@angular/material/dialog';
import { Data } from './data';
import { API, Sample } from '../core/label.service';

const ROWS: Sample[] = [
  { id: 1, image_path: 'english/1.png', text: 'hello', language: 'english', rating: 'correct', engine_guess: 'helo', created_at: '' },
  { id: 2, image_path: 'english/2.png', text: 'world', language: 'english', rating: 'incorrect', engine_guess: 'wrld', created_at: '' },
];

function setup(dialogStub?: unknown) {
  TestBed.configureTestingModule({
    imports: [Data],
    providers: [
      provideHttpClient(),
      provideHttpClientTesting(),
      ...(dialogStub ? [{ provide: MatDialog, useValue: dialogStub }] : []),
    ],
  });
  const fixture = TestBed.createComponent(Data);
  fixture.detectChanges();
  const http = TestBed.inject(HttpTestingController);
  http.expectOne(`${API}/label/samples`).flush(ROWS);
  fixture.detectChanges();
  return { fixture, http };
}

describe('Data', () => {
  it('renders a clickable compact cell per sample', () => {
    const { fixture, http } = setup();
    const el: HTMLElement = fixture.nativeElement;
    expect(el.querySelectorAll('.cell').length).toBe(2);
    expect(el.textContent).toContain('hello');
    http.verify();
  });

  it('filters by rating and by text', () => {
    const { fixture, http } = setup();
    const c = fixture.componentInstance;
    c.setFilter('incorrect');
    expect(c.filtered().map((s) => s.id)).toEqual([2]);
    c.setFilter('all');
    c.query.set('hell');
    expect(c.filtered().map((s) => s.id)).toEqual([1]);
    http.verify();
  });

  it('opens the detail dialog and reloads when it closes', () => {
    const dialog = { open: () => ({ afterClosed: () => of(true) }) };
    const { fixture, http } = setup(dialog);
    fixture.componentInstance.openDetail(ROWS[0]);
    http.expectOne(`${API}/label/samples`).flush(ROWS); // reload after close
    http.verify();
  });
});
