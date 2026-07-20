import { Injectable, signal } from '@angular/core';
import { Language, OcrLine, OcrResult } from '../core/label.service';

@Injectable({ providedIn: 'root' })
export class OcrStateService {
  image = signal<string | null>(null);
  result = signal<OcrResult | null>(null);
  corrected = signal<OcrLine[] | null>(null);
  showCorrected = signal(false);
  loading = signal(false);
  correcting = signal(false);
  exporting = signal(false);
  language = signal<Language>('auto');
}
