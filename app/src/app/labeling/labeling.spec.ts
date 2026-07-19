import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { Labeling } from './labeling';

describe('Labeling', () => {
  it('creates and shows the canvas + Guess button', async () => {
    await TestBed.configureTestingModule({
      imports: [Labeling],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();
    const fixture = TestBed.createComponent(Labeling);
    fixture.detectChanges();
    const el: HTMLElement = fixture.nativeElement;
    expect(el.querySelector('canvas')).toBeTruthy();
    expect(el.textContent).toContain('Guess');
  });
});
