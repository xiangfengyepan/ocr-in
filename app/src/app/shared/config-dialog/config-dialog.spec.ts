import { vi } from 'vitest';
import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { MatDialogRef } from '@angular/material/dialog';
import { ConfigDialog } from './config-dialog';
import { API } from '../../core/label.service';

function setup() {
  TestBed.configureTestingModule({
    imports: [ConfigDialog],
    providers: [
      provideHttpClient(),
      provideHttpClientTesting(),
      { provide: MatDialogRef, useValue: { close: () => undefined } },
    ],
  });
  const fixture = TestBed.createComponent(ConfigDialog);
  const http = TestBed.inject(HttpTestingController);
  // constructor fetches the current ollama host
  http.expectOne(`${API}/config`).flush({ ollama_host: 'http://localhost:11434' });
  return { c: fixture.componentInstance, http };
}

describe('ConfigDialog', () => {
  it('loads the current ollama host on open', () => {
    const { c, http } = setup();
    expect(c.ollamaHost()).toBe('http://localhost:11434');
    http.verify();
  });

  it('saves: persists apiBase to localStorage and POSTs the ollama host', () => {
    const reload = vi.fn();
    Object.defineProperty(window, 'location', { value: { reload }, writable: true });
    localStorage.removeItem('apiBase');

    const { c, http } = setup();
    c.apiBase.set('https://api.example.com/');
    c.ollamaHost.set('http://box:11434');
    c.save();

    expect(localStorage.getItem('apiBase')).toBe('https://api.example.com'); // trailing slash trimmed
    const req = http.expectOne(`https://api.example.com/config`);
    expect(req.request.method).toBe('POST');
    expect(req.request.body.ollama_host).toBe('http://box:11434');
    req.flush({ ollama_host: 'http://box:11434' });
    http.verify();
  });
});
