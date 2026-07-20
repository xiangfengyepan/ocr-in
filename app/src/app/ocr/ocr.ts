import { Component, inject, signal } from '@angular/core';
import { finalize } from 'rxjs';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { Language, LabelService, OcrResult } from '../core/label.service';
import { ToastService } from '../shared/toast.service';

@Component({
  selector: 'app-ocr',
  imports: [
    MatCardModule,
    MatButtonModule,
    MatProgressSpinnerModule,
    MatSlideToggleModule,
    MatFormFieldModule,
    MatSelectModule,
  ],
  templateUrl: './ocr.html',
  styleUrl: './ocr.scss',
})
export class Ocr {
  private svc = inject(LabelService);
  private toast = inject(ToastService);

  readonly languages: Language[] = ['auto', 'english', 'spanish', 'catalan', 'chinese', 'japanese'];
  image = signal<string | null>(null);
  result = signal<OcrResult | null>(null);
  loading = signal(false);
  correct = signal(false);
  language = signal<Language>('auto');

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

  private load(file: File): void {
    if (!file.type.startsWith('image/')) {
      this.toast.error('Please choose an image file.');
      return;
    }
    const reader = new FileReader();
    reader.onload = () => {
      this.image.set(reader.result as string);
      this.result.set(null);
    };
    reader.readAsDataURL(file);
  }

  setLanguage(l: Language): void {
    this.language.set(l);
  }

  recognize(): void {
    const img = this.image();
    if (!img) return;
    this.loading.set(true);
    this.result.set(null);
    this.svc
      .recognizeImage(img, this.correct(), this.language())
      .pipe(finalize(() => this.loading.set(false)))
      .subscribe({
        next: (r) => this.result.set(r),
        error: () => this.toast.error('Recognition failed — is the API running?'),
      });
  }
}
