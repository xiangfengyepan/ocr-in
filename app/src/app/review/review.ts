import { Component, OnInit, computed, inject, signal, viewChild, ElementRef } from '@angular/core';
import { RouterLink } from '@angular/router';
import { finalize } from 'rxjs';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { LabelService, Sample } from '../core/label.service';
import { ToastService } from '../shared/toast.service';

@Component({
  selector: 'app-review',
  imports: [
    RouterLink,
    MatCardModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatProgressSpinnerModule,
  ],
  templateUrl: './review.html',
  styleUrl: './review.scss',
  host: { '(window:keydown)': 'onKeydown($event)' },
})
export class Review implements OnInit {
  private svc = inject(LabelService);
  private toast = inject(ToastService);
  private fixInput = viewChild<ElementRef<HTMLInputElement>>('fixInput');

  queue = signal<Sample[]>([]);
  index = signal(0);
  loading = signal(false);
  fixing = signal(false);
  fixText = signal('');
  saving = signal(false);

  current = computed<Sample | null>(() => this.queue()[this.index()] ?? null);
  done = computed(() => this.index() >= this.queue().length);

  imageUrl(id: number): string {
    return this.svc.imageUrl(id);
  }

  ngOnInit(): void {
    this.loading.set(true);
    this.svc
      .listSamples('pending')
      .pipe(finalize(() => this.loading.set(false)))
      .subscribe({
        next: (samples) => {
          this.queue.set(samples);
          this.index.set(0);
        },
        error: () => this.toast.error('Could not load the review queue.'),
      });
  }

  markCorrect(): void {
    const sample = this.current();
    if (!sample || this.saving()) return;
    this.saving.set(true);
    this.svc
      .updateSample(sample.id, { rating: 'correct', text: sample.text })
      .pipe(finalize(() => this.saving.set(false)))
      .subscribe({
        next: () => this.advance(),
        error: () => this.toast.error('Could not save.'),
      });
  }

  openFix(): void {
    const sample = this.current();
    if (!sample) return;
    this.fixing.set(true);
    this.fixText.set(sample.text);
    setTimeout(() => this.fixInput()?.nativeElement.focus());
  }

  cancelFix(): void {
    this.fixing.set(false);
  }

  saveFix(): void {
    const sample = this.current();
    if (!sample || this.saving()) return;
    this.saving.set(true);
    this.svc
      .updateSample(sample.id, { rating: 'incorrect', text: this.fixText() })
      .pipe(finalize(() => this.saving.set(false)))
      .subscribe({
        next: () => {
          this.fixing.set(false);
          this.advance();
        },
        error: () => this.toast.error('Could not save.'),
      });
  }

  private advance(): void {
    this.index.update((i) => i + 1);
  }

  onKeydown(event: KeyboardEvent): void {
    const typing = (event.target as HTMLElement)?.tagName === 'INPUT';

    if (this.fixing()) {
      if (event.key === 'Enter') {
        event.preventDefault();
        this.saveFix();
      } else if (event.key === 'Escape') {
        event.preventDefault();
        this.cancelFix();
      }
      return;
    }

    if (typing || !this.current()) return;

    if (event.key === 'c' || event.key === 'C') {
      event.preventDefault();
      this.markCorrect();
    } else if (event.key === 'i' || event.key === 'I') {
      event.preventDefault();
      this.openFix();
    }
  }
}
