import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { finalize } from 'rxjs';
import { ScrollingModule } from '@angular/cdk/scrolling';
import { MatButtonModule } from '@angular/material/button';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatDialog } from '@angular/material/dialog';
import { LabelService, Sample } from '../core/label.service';
import { ToastService } from '../shared/toast.service';
import { SampleDetail } from './sample-detail/sample-detail';

type Filter = 'all' | 'correct' | 'incorrect';

@Component({
  selector: 'app-data',
  imports: [
    ScrollingModule,
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
  importing = signal(false);
  filter = signal<Filter>('all');
  query = signal('');

  filtered = computed(() => {
    const q = this.query().trim().toLowerCase();
    const f = this.filter();
    return this.samples().filter(
      (s) =>
        (f === 'all' || s.rating === f) &&
        (!q ||
          s.text.toLowerCase().includes(q) ||
          (s.engine_guess ?? '').toLowerCase().includes(q)),
    );
  });

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

  setFilter(f: Filter): void {
    this.filter.set(f);
  }

  openDetail(s: Sample): void {
    this.dialog
      .open(SampleDetail, { data: { ...s }, width: '480px', maxWidth: '95vw' })
      .afterClosed()
      .subscribe(() => this.reload());
  }

  exportLabels(): void {
    this.svc.exportLabels().subscribe({
      next: (blob) => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'labels_export.zip';
        a.click();
        URL.revokeObjectURL(url);
      },
      error: () => this.toast.error('Export failed.'),
    });
  }

  onImport(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    input.value = '';
    if (!file) return;
    this.importing.set(true);
    this.svc
      .importLabels(file)
      .pipe(finalize(() => this.importing.set(false)))
      .subscribe({
        next: (r) => {
          this.toast.success(`Imported ${r.imported} sample${r.imported === 1 ? '' : 's'}`);
          this.reload();
        },
        error: () => this.toast.error('Import failed — is it a labels export zip?'),
      });
  }
}
