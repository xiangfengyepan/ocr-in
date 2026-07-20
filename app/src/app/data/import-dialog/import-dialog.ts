import { Component, OnDestroy, computed, inject, signal } from '@angular/core';
import { finalize } from 'rxjs';
import { MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { ImportJob, ImportState, LabelService } from '../../core/label.service';
import { ToastService } from '../../shared/toast.service';

const POLL_INTERVAL_MS = 1500;

@Component({
  selector: 'app-import-dialog',
  imports: [MatDialogModule, MatButtonModule, MatProgressSpinnerModule],
  templateUrl: './import-dialog.html',
  styleUrl: './import-dialog.scss',
})
export class ImportDialog implements OnDestroy {
  private svc = inject(LabelService);
  private toast = inject(ToastService);
  private ref = inject<MatDialogRef<ImportDialog>>(MatDialogRef);
  private pollHandle: ReturnType<typeof setInterval> | null = null;
  private sessionIds = new Set<number>();

  mode = signal<'select' | 'status'>('select');
  files = signal<File[]>([]);
  jobs = signal<ImportJob[]>([]);
  importing = signal(false);
  dragOver = signal(false);

  allDone = computed(() => this.jobs().length > 0 && !this.hasActive(this.jobs()));

  onDragOver(event: DragEvent): void {
    event.preventDefault();
    this.dragOver.set(true);
  }

  onDragLeave(event: DragEvent): void {
    event.preventDefault();
    this.dragOver.set(false);
  }

  onDrop(event: DragEvent): void {
    event.preventDefault();
    this.dragOver.set(false);
    const files = Array.from(event.dataTransfer?.files ?? []);
    if (files.length) this.files.set(files);
  }

  onChoose(event: Event): void {
    const input = event.target as HTMLInputElement;
    this.files.set(input.files ? Array.from(input.files) : []);
  }

  process(): void {
    const files = this.files();
    if (!files.length) return;
    this.importing.set(true);
    this.svc
      .importFiles(files)
      .pipe(finalize(() => this.importing.set(false)))
      .subscribe({
        next: (r) => {
          this.sessionIds = new Set(r.jobs.map((j) => j.id));
          this.jobs.set(r.jobs);
          this.mode.set('status');
          this.startPolling();
        },
        error: () => this.toast.error('Import failed.'),
      });
  }

  private hasActive(jobs: ImportJob[]): boolean {
    return jobs.some((j) => j.state === 'queued' || j.state === 'processing');
  }

  pollStatus(): void {
    this.svc.importStatus().subscribe((jobs) => {
      const mine = jobs.filter((j) => this.sessionIds.has(j.id));
      this.jobs.set(mine);
      if (!this.hasActive(mine)) this.stopPolling();
    });
  }

  private startPolling(): void {
    this.pollStatus();
    if (this.pollHandle) return;
    this.pollHandle = setInterval(() => this.pollStatus(), POLL_INTERVAL_MS);
  }

  private stopPolling(): void {
    if (this.pollHandle) {
      clearInterval(this.pollHandle);
      this.pollHandle = null;
    }
  }

  stateClass(state: ImportState): string {
    return `state-${state}`;
  }

  close(): void {
    this.ref.close();
  }

  ngOnDestroy(): void {
    this.stopPolling();
  }
}
