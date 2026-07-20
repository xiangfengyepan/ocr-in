import { Component, OnDestroy, OnInit, inject, signal } from '@angular/core';
import { finalize } from 'rxjs';
import { RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatIconModule } from '@angular/material/icon';
import { MatPaginatorModule, PageEvent } from '@angular/material/paginator';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatDialog } from '@angular/material/dialog';
import { LabelService, Rating, Sample } from '../core/label.service';
import { ToastService } from '../shared/toast.service';
import { SampleDetail } from './sample-detail/sample-detail';
import { ImportDialog } from './import-dialog/import-dialog';
import { ConfirmDialog } from '../shared/components/confirm-dialog/confirm-dialog';

type Filter = 'all' | 'pending' | 'correct' | 'incorrect';

const SEARCH_DEBOUNCE_MS = 300;

@Component({
  selector: 'app-data',
  imports: [
    RouterLink,
    MatButtonModule,
    MatButtonToggleModule,
    MatFormFieldModule,
    MatInputModule,
    MatIconModule,
    MatPaginatorModule,
    MatProgressSpinnerModule,
  ],
  templateUrl: './data.html',
  styleUrl: './data.scss',
})
export class Data implements OnInit, OnDestroy {
  private svc = inject(LabelService);
  private toast = inject(ToastService);
  private dialog = inject(MatDialog);
  private searchTimer?: ReturnType<typeof setTimeout>;

  samples = signal<Sample[]>([]);
  total = signal(0);
  loading = signal(false);
  importing = signal(false);
  filter = signal<Filter>('all');
  query = signal('');
  pageIndex = signal(0);
  pageSize = signal(25);
  selectedId = signal<number | null>(null);
  pendingCount = signal(0);

  ngOnInit(): void {
    this.reload();
    this.refreshStats();
  }

  ngOnDestroy(): void {
    if (this.searchTimer) clearTimeout(this.searchTimer);
  }

  private ratingParam(): Rating | undefined {
    const f = this.filter();
    return f === 'all' ? undefined : f;
  }

  reload(): void {
    this.loading.set(true);
    const rating = this.ratingParam();
    const q = this.query().trim() || undefined;
    const offset = this.pageIndex() * this.pageSize();
    this.svc.countSamples({ rating, q }).subscribe((n) => this.total.set(n));
    this.svc
      .pageSamples({ rating, q, limit: this.pageSize(), offset })
      .pipe(finalize(() => this.loading.set(false)))
      .subscribe((rows) => this.samples.set(rows));
  }

  refreshStats(): void {
    this.svc.stats().subscribe((s) => this.pendingCount.set(s.by_rating['pending'] ?? 0));
  }

  imageUrl(id: number): string {
    return this.svc.imageUrl(id);
  }

  setFilter(f: Filter): void {
    this.filter.set(f);
    this.pageIndex.set(0);
    this.reload();
  }

  onQuery(value: string): void {
    this.query.set(value);
    if (this.searchTimer) clearTimeout(this.searchTimer);
    this.searchTimer = setTimeout(() => {
      this.pageIndex.set(0);
      this.reload();
    }, SEARCH_DEBOUNCE_MS);
  }

  onPage(event: PageEvent): void {
    this.pageIndex.set(event.pageIndex);
    this.pageSize.set(event.pageSize);
    this.reload();
  }

  select(s: Sample): void {
    this.selectedId.set(s.id);
  }

  openDetail(s: Sample): void {
    this.selectedId.set(s.id);
    this.dialog
      .open(SampleDetail, { data: { ...s }, width: '480px', maxWidth: '95vw' })
      .afterClosed()
      .subscribe(() => {
        this.reload();
        this.refreshStats();
      });
  }

  deleteRow(s: Sample, event: Event): void {
    event.stopPropagation();
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
            this.toast.success('Sample deleted');
            this.reload();
            this.refreshStats();
          },
          error: () => this.toast.error('Could not delete the sample.'),
        });
      });
  }

  openImport(): void {
    this.dialog
      .open(ImportDialog, { width: '520px', maxWidth: '95vw' })
      .afterClosed()
      .subscribe(() => {
        this.reload();
        this.refreshStats();
      });
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

  importZip(event: Event): void {
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
          this.toast.success(`Imported ${r.imported} label${r.imported === 1 ? '' : 's'}`);
          this.reload();
          this.refreshStats();
        },
        error: () => this.toast.error('Label import failed.'),
      });
  }
}
