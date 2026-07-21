import { Component, OnDestroy, OnInit, inject, signal } from '@angular/core';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatDialog } from '@angular/material/dialog';
import { LabelService, ModelInfo, TrainJob, TrainKind } from '../core/label.service';
import { ToastService } from '../shared/toast.service';
import { ModelChart } from './model-chart/model-chart';

const POLL_INTERVAL_MS = 2000;
const ACTIVE_STATES = new Set(['queued', 'training', 'evaluating']);
const KINDS: TrainKind[] = ['line', 'word'];

@Component({
  selector: 'app-models',
  imports: [MatCardModule, MatButtonModule, MatTooltipModule, MatProgressSpinnerModule],
  templateUrl: './models.html',
  styleUrl: './models.scss',
})
export class Models implements OnInit, OnDestroy {
  private svc = inject(LabelService);
  private dialog = inject(MatDialog);
  private toast = inject(ToastService);
  private pollHandle: ReturnType<typeof setInterval> | null = null;

  readonly kinds: TrainKind[] = KINDS;

  models = signal<ModelInfo[]>([]);
  jobs = signal<Record<TrainKind, TrainJob | null>>({ line: null, word: null });
  promoting = signal<Record<TrainKind, boolean>>({ line: false, word: false });

  ngOnInit(): void {
    this.reload();
  }

  ngOnDestroy(): void {
    this.stopPolling();
  }

  reload(): void {
    this.svc.models().subscribe((m) => this.models.set(m));
  }

  pct(v: number | null | undefined): string {
    return v == null ? '—' : `${(v * 100).toFixed(1)}%`;
  }

  delta(base: number | null, next: number | null): string {
    if (base == null || next == null) return '—';
    const d = (next - base) * 100;
    const sign = d > 0 ? '+' : '';
    return `${sign}${d.toFixed(1)}%`;
  }

  isActive(job: TrainJob | null): boolean {
    return !!job && ACTIVE_STATES.has(job.state);
  }

  open(m: ModelInfo): void {
    this.dialog.open(ModelChart, { data: m, width: '540px', maxWidth: '95vw' });
  }

  train(kind: TrainKind): void {
    if (this.isActive(this.jobs()[kind])) return;
    this.svc.startTrain(kind).subscribe({
      next: (r) => {
        this.jobs.update((j) => ({ ...j, [kind]: r.job }));
        this.startPolling();
      },
      error: () => this.toast.error('Could not start training.'),
    });
  }

  promote(kind: TrainKind): void {
    const job = this.jobs()[kind];
    if (!job) return;
    this.promoting.update((p) => ({ ...p, [kind]: true }));
    this.svc.promoteModel(job.id).subscribe({
      next: () => {
        this.promoting.update((p) => ({ ...p, [kind]: false }));
        this.jobs.update((j) => {
          const current = j[kind];
          return current ? { ...j, [kind]: { ...current, promoted: true } } : j;
        });
        this.reload();
        this.toast.success('Model promoted.');
      },
      error: () => {
        this.promoting.update((p) => ({ ...p, [kind]: false }));
        this.toast.error('Could not promote model.');
      },
    });
  }

  private startPolling(): void {
    if (this.pollHandle) return;
    this.pollHandle = setInterval(() => this.pollStatus(), POLL_INTERVAL_MS);
  }

  private stopPolling(): void {
    if (this.pollHandle) {
      clearInterval(this.pollHandle);
      this.pollHandle = null;
    }
  }

  pollStatus(): void {
    this.svc.trainStatus().subscribe((all) => {
      const current = this.jobs();
      const next: Record<TrainKind, TrainJob | null> = { ...current };
      for (const kind of KINDS) {
        const tracked = current[kind];
        if (!tracked) continue;
        const updated = all.find((j) => j.id === tracked.id);
        if (updated) next[kind] = updated;
      }
      this.jobs.set(next);
      if (!KINDS.some((k) => this.isActive(next[k]))) this.stopPolling();
    });
  }
}
