import { Component, inject, signal } from '@angular/core';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatTabsModule } from '@angular/material/tabs';
import { LabelService, ModelInfo, StatsResponse } from '../../core/label.service';

@Component({
  selector: 'app-model-chart',
  imports: [MatDialogModule, MatButtonModule, MatTabsModule],
  templateUrl: './model-chart.html',
  styleUrl: './model-chart.scss',
})
export class ModelChart {
  data = inject<ModelInfo>(MAT_DIALOG_DATA);
  private ref = inject<MatDialogRef<ModelChart>>(MatDialogRef);
  private svc = inject(LabelService);
  stats = signal<StatsResponse | null>(null);

  constructor() {
    this.svc.stats().subscribe((s) => this.stats.set(s));
  }

  ratingPct(s: StatsResponse, key: string): number {
    return s.total ? ((s.by_rating[key] || 0) / s.total) * 100 : 0;
  }

  bench(): { cer: number; wer: number } | null {
    const m = this.data.metrics;
    return this.data.best_for === 'lines' ? m.lines : this.data.best_for === 'words' ? m.words : null;
  }

  readonly W = 460;
  readonly H = 240;
  readonly pad = 40;
  readonly history = this.data.history ?? [];
  readonly maxY = Math.max(0.001, ...this.history.flatMap((h) => [h.cer, h.wer]));

  private x(i: number): number {
    const n = this.history.length;
    return this.pad + (n <= 1 ? 0 : (i / (n - 1)) * (this.W - 2 * this.pad));
  }

  private y(v: number): number {
    return this.H - this.pad - (v / this.maxY) * (this.H - 2 * this.pad);
  }

  points(key: 'cer' | 'wer'): string {
    return this.history.map((h, i) => `${this.x(i).toFixed(1)},${this.y(h[key]).toFixed(1)}`).join(' ');
  }

  yTicks(): { v: number; y: number }[] {
    return [0, this.maxY / 2, this.maxY].map((v) => ({ v, y: this.y(v) }));
  }

  get lastEpoch(): number {
    return this.history.length ? this.history[this.history.length - 1].epoch : 0;
  }

  get axisY(): number {
    return this.H - this.pad;
  }

  close(): void {
    this.ref.close();
  }
}
