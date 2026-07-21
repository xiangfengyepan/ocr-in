import { Component, OnInit, inject, signal } from '@angular/core';
import { MatCardModule } from '@angular/material/card';
import { MatDialog } from '@angular/material/dialog';
import { LabelService, ModelInfo } from '../core/label.service';
import { ModelChart } from './model-chart/model-chart';

@Component({
  selector: 'app-models',
  imports: [MatCardModule],
  templateUrl: './models.html',
  styleUrl: './models.scss',
})
export class Models implements OnInit {
  private svc = inject(LabelService);
  private dialog = inject(MatDialog);

  models = signal<ModelInfo[]>([]);

  ngOnInit(): void {
    this.reload();
  }

  reload(): void {
    this.svc.models().subscribe((m) => this.models.set(m));
  }

  pct(v: number | null | undefined): string {
    return v == null ? '—' : `${(v * 100).toFixed(1)}%`;
  }

  open(m: ModelInfo): void {
    this.dialog.open(ModelChart, { data: m, width: '540px', maxWidth: '95vw' });
  }
}
