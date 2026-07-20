import {
  AfterViewInit,
  Component,
  ElementRef,
  OnDestroy,
  inject,
  signal,
  viewChild,
} from '@angular/core';
import { DecimalPipe } from '@angular/common';
import { finalize } from 'rxjs';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { Kind, Language, LabelService } from '../core/label.service';
import { ToastService } from '../shared/toast.service';

type Rating = 'correct' | 'incorrect';

const DETECT_DEBOUNCE_MS = 400;

@Component({
  selector: 'app-labeling',
  imports: [
    DecimalPipe,
    MatCardModule,
    MatButtonModule,
    MatButtonToggleModule,
    MatFormFieldModule,
    MatInputModule,
    MatProgressSpinnerModule,
    MatSelectModule,
  ],
  templateUrl: './labeling.html',
  styleUrl: './labeling.scss',
  host: { '(window:paste)': 'onPaste($event)' },
})
export class Labeling implements AfterViewInit, OnDestroy {
  private svc = inject(LabelService);
  private toast = inject(ToastService);
  private canvasRef = viewChild.required<ElementRef<HTMLCanvasElement>>('canvas');
  private ctx: CanvasRenderingContext2D | null = null;
  private drawing = false;
  private detectTimer?: ReturnType<typeof setTimeout>;

  guess = signal<string | null>(null);
  confidence = signal(0);
  rating = signal<Rating | null>(null);
  text = signal('');
  total = signal(0);
  guessing = signal(false);
  saving = signal(false);
  mode = signal<Kind>('word');
  detecting = signal(false);
  engine = signal<string | null>(null);
  readonly languages: Language[] = ['auto', 'english', 'spanish', 'catalan', 'chinese', 'japanese'];
  language = signal<Language>('auto');
  corrected = signal<string | null>(null);
  correcting = signal(false);
  detectedLang = signal<string | null>(null);

  ngAfterViewInit(): void {
    const ctx = this.canvasRef().nativeElement.getContext('2d');
    if (!ctx) return;
    this.ctx = ctx;
    this.clear();
    this.refreshStats();
  }

  ngOnDestroy(): void {
    if (this.detectTimer) clearTimeout(this.detectTimer);
  }

  onPointerDown(e: PointerEvent): void { this.drawing = true; this.stroke(e); }
  onPointerUp(): void {
    if (!this.drawing) return;
    this.drawing = false;
    this.ctx?.beginPath();
    this.scheduleDetect();
  }
  onPointerMove(e: PointerEvent): void { if (this.drawing) this.stroke(e); }

  private stroke(e: PointerEvent): void {
    if (!this.ctx) return;
    const rect = this.canvasRef().nativeElement.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    this.ctx.lineWidth = 6;
    this.ctx.lineCap = 'round';
    this.ctx.strokeStyle = '#000';
    this.ctx.lineTo(x, y);
    this.ctx.stroke();
    this.ctx.beginPath();
    this.ctx.moveTo(x, y);
  }

  clear(): void {
    if (this.detectTimer) clearTimeout(this.detectTimer);
    if (this.ctx) {
      const c = this.canvasRef().nativeElement;
      this.ctx.fillStyle = '#fff';
      this.ctx.fillRect(0, 0, c.width, c.height);
      this.ctx.beginPath();
    }
    this.guess.set(null);
    this.rating.set(null);
    this.text.set('');
    this.engine.set(null);
    this.corrected.set(null);
    this.detectedLang.set(null);
  }

  setLanguage(l: Language): void {
    this.language.set(l);
  }

  private png(): string { return this.canvasRef().nativeElement.toDataURL('image/png'); }

  onImageSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    input.value = '';
    if (file) this.loadImageFile(file);
  }

  onDragOver(event: DragEvent): void {
    event.preventDefault();
  }

  onDrop(event: DragEvent): void {
    event.preventDefault();
    const file = event.dataTransfer?.files?.[0];
    if (file) this.loadImageFile(file);
  }

  onPaste(event: ClipboardEvent): void {
    const item = Array.from(event.clipboardData?.items ?? []).find((i) =>
      i.type.startsWith('image/'),
    );
    const file = item?.getAsFile();
    if (file) this.loadImageFile(file);
  }

  private loadImageFile(file: File): void {
    if (!file.type.startsWith('image/')) {
      this.toast.error('Please choose an image file.');
      return;
    }
    const img = new Image();
    const url = URL.createObjectURL(file);
    img.onload = () => {
      this.drawImage(img);
      URL.revokeObjectURL(url);
    };
    img.onerror = () => {
      this.toast.error('Could not load that image.');
      URL.revokeObjectURL(url);
    };
    img.src = url;
  }

  private drawImage(img: HTMLImageElement): void {
    if (!this.ctx) return;
    const c = this.canvasRef().nativeElement;
    this.ctx.fillStyle = '#fff';
    this.ctx.fillRect(0, 0, c.width, c.height);
    const scale = Math.min(c.width / img.width, c.height / img.height);
    const w = img.width * scale;
    const h = img.height * scale;
    this.ctx.drawImage(img, (c.width - w) / 2, (c.height - h) / 2, w, h);
    this.ctx.beginPath();
    this.guess.set(null);
    this.rating.set(null);
    this.text.set('');
    this.corrected.set(null);
    this.detectedLang.set(null);
    this.engine.set(null);
    this.scheduleDetect();
  }

  private scheduleDetect(): void {
    if (this.detectTimer) clearTimeout(this.detectTimer);
    this.detectTimer = setTimeout(() => {
      this.detecting.set(true);
      this.svc
        .detect(this.png())
        .pipe(finalize(() => this.detecting.set(false)))
        .subscribe({ next: (r) => this.mode.set(r.kind) });
    }, DETECT_DEBOUNCE_MS);
  }

  setMode(m: Kind): void {
    this.mode.set(m);
  }

  doGuess(): void {
    this.guessing.set(true);
    this.svc
      .guess(this.png(), this.mode())
      .pipe(finalize(() => this.guessing.set(false)))
      .subscribe({
        next: (r) => {
          this.guess.set(r.guess);
          this.confidence.set(r.confidence);
          this.text.set(r.guess);
          this.engine.set(r.engine);
          this.rating.set(null);
          this.correctStep(r.guess);
        },
        error: () =>
          this.toast.error('Guess failed — check the API is running and the model is available.'),
      });
  }

  private correctStep(raw: string): void {
    this.correcting.set(true);
    this.corrected.set(null);
    this.svc
      .correct(raw, this.language(), this.mode())
      .pipe(finalize(() => this.correcting.set(false)))
      .subscribe({
        next: (c) => {
          this.corrected.set(c.corrected);
          this.detectedLang.set(c.language);
          this.text.set(c.corrected);
        },
        error: () => this.toast.error('Correction failed — keeping the raw OCR text.'),
      });
  }

  rate(r: Rating): void {
    this.rating.set(r);
    if (r === 'correct') this.text.set(this.corrected() ?? this.guess() ?? '');
  }

  save(): void {
    if (!this.rating()) return;
    this.saving.set(true);
    this.svc
      .sample({
        image: this.png(),
        rating: this.rating()!,
        text: this.text(),
        engine_guess: this.guess(),
      })
      .pipe(finalize(() => this.saving.set(false)))
      .subscribe({
        next: () => {
          this.toast.success('Sample saved');
          this.clear();
          this.refreshStats();
        },
        error: () => this.toast.error('Could not save the sample.'),
      });
  }

  refreshStats(): void { this.svc.stats().subscribe((s) => this.total.set(s.total)); }
}
