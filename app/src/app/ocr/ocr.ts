import { Component, computed, inject, signal } from '@angular/core';
import { finalize } from 'rxjs';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { Language, LabelService, OcrLine } from '../core/label.service';
import { ToastService } from '../shared/toast.service';
import { OcrStateService } from './ocr-state.service';

@Component({
  selector: 'app-ocr',
  imports: [
    MatCardModule,
    MatButtonModule,
    MatProgressSpinnerModule,
    MatFormFieldModule,
    MatSelectModule,
  ],
  templateUrl: './ocr.html',
  styleUrl: './ocr.scss',
  host: { '(window:paste)': 'onPaste($event)' },
})
export class Ocr {
  private svc = inject(LabelService);
  private toast = inject(ToastService);
  private state = inject(OcrStateService);

  readonly languages: Language[] = ['auto', 'english', 'spanish', 'catalan', 'chinese', 'japanese'];
  image = this.state.image;
  result = this.state.result;
  corrected = this.state.corrected;
  showCorrected = this.state.showCorrected;
  loading = this.state.loading;
  correcting = this.state.correcting;
  exporting = this.state.exporting;
  language = this.state.language;
  saving = signal(false);

  displayLines = computed<OcrLine[]>(() => {
    const r = this.result();
    if (!r) return [];
    const c = this.corrected();
    return this.showCorrected() && c ? c : r.lines;
  });
  displayText = computed(() => this.displayLines().map((l) => l.text).join('\n'));

  onFile(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    input.value = '';
    if (file) this.load(file);
  }

  onDrop(event: DragEvent): void {
    event.preventDefault();
    const file = event.dataTransfer?.files?.[0];
    if (file) this.load(file);
  }

  onDragOver(event: DragEvent): void {
    event.preventDefault();
  }

  onPaste(event: ClipboardEvent): void {
    const item = Array.from(event.clipboardData?.items ?? []).find((i) =>
      i.type.startsWith('image/'),
    );
    const file = item?.getAsFile();
    if (file) this.load(file);
  }

  private load(file: File): void {
    if (!file.type.startsWith('image/')) {
      this.toast.error('Please choose an image file.');
      return;
    }
    const reader = new FileReader();
    reader.onload = () => {
      this.image.set(reader.result as string);
      this.reset();
    };
    reader.readAsDataURL(file);
  }

  private reset(): void {
    this.result.set(null);
    this.corrected.set(null);
    this.showCorrected.set(false);
  }

  setLanguage(l: Language): void {
    this.language.set(l);
  }

  lineStyle(ln: OcrLine): Record<string, string> {
    const r = this.result();
    if (!r) return {};
    const [x0, y0, x1, y1] = ln.box;
    return {
      left: `${(x0 / r.width) * 100}%`,
      top: `${(y0 / r.height) * 100}%`,
      width: `${((x1 - x0) / r.width) * 100}%`,
      height: `${((y1 - y0) / r.height) * 100}%`,
      'font-size': `${((y1 - y0) / r.width) * 100}cqw`,
    };
  }

  copyAll(): void {
    navigator.clipboard?.writeText(this.displayText()).then(
      () => this.toast.success('Text copied'),
      () => this.toast.error('Copy failed'),
    );
  }

  editLine(index: number, event: Event): void {
    const text = (event.target as HTMLElement).innerText.replace(/\n+$/, '');
    if (this.showCorrected() && this.corrected()) {
      this.corrected.update((lines) =>
        lines ? lines.map((ln, i) => (i === index ? { ...ln, text } : ln)) : lines,
      );
    } else {
      this.result.update((r) => {
        if (!r) return r;
        const lines = r.lines.map((ln, i) => (i === index ? { ...ln, text } : ln));
        return { ...r, lines, text: lines.map((l) => l.text).join('\n') };
      });
    }
  }

  correctClick(): void {
    // First click fetches + shows the AI-corrected version; later clicks flip
    // between the original OCR and the corrected text.
    if (this.corrected() === null) {
      this.toggleCorrected(true);
    } else {
      this.showCorrected.update((v) => !v);
    }
  }

  toggleCorrected(on: boolean): void {
    if (!on) {
      this.showCorrected.set(false);
      return;
    }
    if (this.corrected()) {
      this.showCorrected.set(true);
      return;
    }
    const r = this.result();
    if (!r) return;
    this.correcting.set(true);
    this.svc
      .correctLines(r.lines, this.language())
      .pipe(finalize(() => this.correcting.set(false)))
      .subscribe({
        next: (res) => {
          this.corrected.set(res.lines);
          this.showCorrected.set(true);
        },
        error: () => this.toast.error('Correction failed — is Ollama running?'),
      });
  }

  exportPdf(): void {
    const img = this.image();
    const r = this.result();
    if (!img || !r) return;
    this.exporting.set(true);
    this.svc
      .exportPdf(img, r.width, r.height, this.displayLines())
      .pipe(finalize(() => this.exporting.set(false)))
      .subscribe({
        next: (blob) => {
          const url = URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = 'ocr.pdf';
          a.click();
          URL.revokeObjectURL(url);
        },
        error: () => this.toast.error('PDF export failed'),
      });
  }

  saveToData(): void {
    const img = this.image();
    const r = this.result();
    if (!img || !r) return;
    const lines = this.displayLines().map((ln, i) => ({
      box: ln.box,
      text: ln.text,
      guess: r.lines[i]?.text ?? null,
    }));
    this.saving.set(true);
    this.svc
      .saveOcr(img, this.language(), lines)
      .pipe(finalize(() => this.saving.set(false)))
      .subscribe({
        next: (res) =>
          this.toast.success(`Saved ${res.saved} line${res.saved === 1 ? '' : 's'} to Data`),
        error: () => this.toast.error('Save failed'),
      });
  }

  recognize(): void {
    const img = this.image();
    if (!img) return;
    this.loading.set(true);
    this.reset();
    this.svc
      .recognizeImage(img)
      .pipe(finalize(() => this.loading.set(false)))
      .subscribe({
        next: (r) => this.result.set(r),
        error: () => this.toast.error('Recognition failed — is the API running?'),
      });
  }
}
