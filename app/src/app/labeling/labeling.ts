import { AfterViewInit, Component, ElementRef, inject, signal, viewChild } from '@angular/core';
import { DecimalPipe } from '@angular/common';
import { finalize } from 'rxjs';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { LabelService } from '../core/label.service';
import { ToastService } from '../shared/toast.service';

type Rating = 'correct' | 'incorrect';

@Component({
  selector: 'app-labeling',
  imports: [
    DecimalPipe,
    MatCardModule,
    MatButtonModule,
    MatButtonToggleModule,
    MatFormFieldModule,
    MatSelectModule,
    MatInputModule,
    MatProgressSpinnerModule,
  ],
  templateUrl: './labeling.html',
  styleUrl: './labeling.scss',
})
export class Labeling implements AfterViewInit {
  private svc = inject(LabelService);
  private toast = inject(ToastService);
  private canvasRef = viewChild.required<ElementRef<HTMLCanvasElement>>('canvas');
  private ctx: CanvasRenderingContext2D | null = null;
  private drawing = false;

  readonly languages = ['english', 'spanish', 'catalan', 'japanese', 'math'];
  language = signal('english');
  guess = signal<string | null>(null);
  confidence = signal(0);
  rating = signal<Rating | null>(null);
  text = signal('');
  total = signal(0);
  guessing = signal(false);
  saving = signal(false);

  ngAfterViewInit(): void {
    const ctx = this.canvasRef().nativeElement.getContext('2d');
    if (!ctx) return;
    this.ctx = ctx;
    this.clear();
    this.refreshStats();
  }

  onPointerDown(e: PointerEvent): void { this.drawing = true; this.stroke(e); }
  onPointerUp(): void { this.drawing = false; this.ctx?.beginPath(); }
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
    if (this.ctx) {
      const c = this.canvasRef().nativeElement;
      this.ctx.fillStyle = '#fff';
      this.ctx.fillRect(0, 0, c.width, c.height);
      this.ctx.beginPath();
    }
    this.guess.set(null);
    this.rating.set(null);
    this.text.set('');
  }

  private png(): string { return this.canvasRef().nativeElement.toDataURL('image/png'); }

  doGuess(): void {
    this.guessing.set(true);
    this.svc
      .guess(this.png(), this.language())
      .pipe(finalize(() => this.guessing.set(false)))
      .subscribe({
        next: (r) => {
          this.guess.set(r.guess);
          this.confidence.set(r.confidence);
          this.text.set(r.guess);
          this.rating.set(null);
        },
        error: () =>
          this.toast.error('Guess failed — check the API is running and a CRNN model is available.'),
      });
  }

  rate(r: Rating): void {
    this.rating.set(r);
    if (r === 'correct') this.text.set(this.guess() ?? '');
  }

  save(): void {
    if (!this.rating()) return;
    this.saving.set(true);
    this.svc
      .sample({
        image: this.png(),
        language: this.language(),
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
