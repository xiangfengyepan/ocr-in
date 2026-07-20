import { Component, OnInit, inject, signal } from '@angular/core';
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
export class Data implements OnInit {
  private svc = inject(LabelService);
  private toast = inject(ToastService);
  private dialog = inject(MatDialog);
  samples = signal<Sample[]>([]);
  loading = signal(false);

  ngOnInit(): void {
    this.reload();
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

  setText(s: Sample, value: string): void {
    s.text = value;
  }

  setRating(s: Sample, rating: Rating): void {
    s.rating = rating;
    this.samples.set([...this.samples()]);
  }

  save(s: Sample): void {
    this.svc.updateSample(s.id, { text: s.text, rating: s.rating }).subscribe({
      next: () => this.toast.success('Sample updated'),
      error: () => this.toast.error('Could not update the sample.'),
    });
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
}
