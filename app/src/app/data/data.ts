import { Component, OnDestroy, OnInit, inject, signal } from '@angular/core';
import { finalize } from 'rxjs';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatDialog } from '@angular/material/dialog';
import { LabelService, Rating, Sample } from '../core/label.service';
import { ToastService } from '../shared/toast.service';
import { ConfirmDialog } from '../shared/components/confirm-dialog/confirm-dialog';

const TEXT_DEBOUNCE_MS = 700;

@Component({
  selector: 'app-data',
  imports: [
    MatCardModule,
    MatButtonModule,
    MatButtonToggleModule,
    MatFormFieldModule,
    MatInputModule,
    MatProgressSpinnerModule,
  ],
  templateUrl: './data.html',
  styleUrl: './data.scss',
})
export class Data implements OnInit, OnDestroy {
  private svc = inject(LabelService);
  private toast = inject(ToastService);
  private dialog = inject(MatDialog);
  private saveTimers = new Map<number, ReturnType<typeof setTimeout>>();

  samples = signal<Sample[]>([]);
  loading = signal(false);
  savingIds = signal<Set<number>>(new Set());

  ngOnInit(): void {
    this.reload();
  }

  ngOnDestroy(): void {
    for (const timer of this.saveTimers.values()) clearTimeout(timer);
  }

  reload(): void {
    this.loading.set(true);
    this.svc
      .listSamples()
      .pipe(finalize(() => this.loading.set(false)))
      .subscribe((rows) => this.samples.set(rows));
  }

  imageUrl(id: number): string {
    return this.svc.imageUrl(id);
  }

  isSaving(id: number): boolean {
    return this.savingIds().has(id);
  }

  setText(s: Sample, value: string): void {
    s.text = value;
    const existing = this.saveTimers.get(s.id);
    if (existing) clearTimeout(existing);
    this.saveTimers.set(
      s.id,
      setTimeout(() => {
        this.saveTimers.delete(s.id);
        this.persist(s);
      }, TEXT_DEBOUNCE_MS),
    );
  }

  setRating(s: Sample, rating: Rating): void {
    s.rating = rating;
    this.samples.set([...this.samples()]);
    this.persist(s);
  }

  remove(s: Sample): void {
    this.dialog
      .open(ConfirmDialog, {
        data: {
          title: 'Delete sample',
          message: `Delete "${s.text}"? This cannot be undone.`,
          confirmLabel: 'Delete',
        },
      })
      .afterClosed()
      .subscribe((confirmed) => {
        if (!confirmed) return;
        this.svc.deleteSample(s.id).subscribe({
          next: () => {
            this.samples.set(this.samples().filter((x) => x.id !== s.id));
            this.toast.success('Sample deleted');
          },
          error: () => this.toast.error('Could not delete the sample.'),
        });
      });
  }

  private persist(s: Sample): void {
    this.setSaving(s.id, true);
    this.svc
      .updateSample(s.id, { text: s.text, rating: s.rating })
      .pipe(finalize(() => this.setSaving(s.id, false)))
      .subscribe({
        error: () => this.toast.error('Could not save the change.'),
      });
  }

  private setSaving(id: number, on: boolean): void {
    const next = new Set(this.savingIds());
    if (on) next.add(id);
    else next.delete(id);
    this.savingIds.set(next);
  }
}
