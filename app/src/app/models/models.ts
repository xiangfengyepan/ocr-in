import { Component, OnInit, inject, signal } from '@angular/core';
import { MatCardModule } from '@angular/material/card';
import { LabelService, ModelInfo } from '../core/label.service';

@Component({
  selector: 'app-models',
  imports: [MatCardModule],
  templateUrl: './models.html',
  styleUrl: './models.scss',
})
export class Models implements OnInit {
  private svc = inject(LabelService);
  models = signal<ModelInfo[]>([]);

  ngOnInit(): void {
    this.svc.models().subscribe((m) => this.models.set(m));
  }

  pct(v: number | null | undefined): string {
    return v == null ? '—' : `${(v * 100).toFixed(1)}%`;
  }
}
