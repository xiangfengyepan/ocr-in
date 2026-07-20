import { Component, OnDestroy, inject, signal } from '@angular/core';
import { finalize } from 'rxjs';
import { MAT_DIALOG_DATA, MatDialog, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { LabelService, Rating, Sample } from '../../core/label.service';
import { ToastService } from '../../shared/toast.service';
import { ConfirmDialog } from '../../shared/components/confirm-dialog/confirm-dialog';

const TEXT_DEBOUNCE_MS = 700;

@Component({
  selector: 'app-sample-detail',
  imports: [
    MatDialogModule,
    MatButtonModule,
    MatButtonToggleModule,
    MatFormFieldModule,
    MatInputModule,
    MatProgressSpinnerModule,
  ],
  templateUrl: './sample-detail.html',
  styleUrl: './sample-detail.scss',
})
export class SampleDetail implements OnDestroy {
  private svc = inject(LabelService);
  private toast = inject(ToastService);
  private dialog = inject(MatDialog);
  private ref = inject<MatDialogRef<SampleDetail>>(MatDialogRef);
  private timer?: ReturnType<typeof setTimeout>;

  sample = inject<Sample>(MAT_DIALOG_DATA);
  saving = signal(false);

  imageUrl(): string {
    return this.svc.imageUrl(this.sample.id);
  }

  setText(value: string): void {
    this.sample.text = value;
    if (this.timer) clearTimeout(this.timer);
    this.timer = setTimeout(() => this.persist(), TEXT_DEBOUNCE_MS);
  }

  setRating(rating: Rating): void {
    this.sample.rating = rating;
    this.persist();
  }

  remove(): void {
    this.dialog
      .open(ConfirmDialog, {
        data: {
          title: 'Delete sample',
          message: `Delete "${this.sample.text}"? This cannot be undone.`,
          confirmLabel: 'Delete',
        },
      })
      .afterClosed()
      .subscribe((confirmed) => {
        if (!confirmed) return;
        this.svc.deleteSample(this.sample.id).subscribe({
          next: () => {
            this.toast.success('Sample deleted');
            this.ref.close();
          },
          error: () => this.toast.error('Could not delete the sample.'),
        });
      });
  }

  close(): void {
    this.ref.close();
  }

  ngOnDestroy(): void {
    if (this.timer) clearTimeout(this.timer);
  }

  private persist(): void {
    this.saving.set(true);
    this.svc
      .updateSample(this.sample.id, { text: this.sample.text, rating: this.sample.rating })
      .pipe(finalize(() => this.saving.set(false)))
      .subscribe({ error: () => this.toast.error('Could not save the change.') });
  }
}
