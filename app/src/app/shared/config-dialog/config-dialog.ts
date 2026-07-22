import { Component, inject, signal } from '@angular/core';
import { finalize } from 'rxjs';
import { MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { API, LabelService, setApiBase } from '../../core/label.service';
import { ToastService } from '../toast.service';

@Component({
  selector: 'app-config-dialog',
  imports: [MatDialogModule, MatButtonModule, MatFormFieldModule, MatInputModule],
  templateUrl: './config-dialog.html',
  styleUrl: './config-dialog.scss',
})
export class ConfigDialog {
  private ref = inject<MatDialogRef<ConfigDialog>>(MatDialogRef);
  private svc = inject(LabelService);
  private toast = inject(ToastService);

  apiBase = signal(API);
  ollamaHost = signal('');
  loading = signal(true);
  saving = signal(false);

  constructor() {
    this.svc.getConfig().subscribe({
      next: (c) => {
        this.ollamaHost.set(c.ollama_host);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  save(): void {
    const api = this.apiBase().trim().replace(/\/+$/, '');
    const ollama = this.ollamaHost().trim();
    // Point the frontend at the chosen backend first (persisted in the browser),
    // then push the Ollama host to that backend.
    if (api) {
      localStorage.setItem('apiBase', api);
      setApiBase(api);
    }
    this.saving.set(true);
    this.svc
      .setConfig(ollama)
      .pipe(finalize(() => this.saving.set(false)))
      .subscribe({
        next: () => {
          this.toast.success('Configuration saved — reloading');
          setTimeout(() => location.reload(), 400);
        },
        error: () => {
          this.toast.error('Saved API base, but could not reach the backend to set the Ollama host');
          setTimeout(() => location.reload(), 800);
        },
      });
  }

  resetApi(): void {
    localStorage.removeItem('apiBase');
    this.toast.success('API base reset to default — reloading');
    setTimeout(() => location.reload(), 400);
  }

  close(): void {
    this.ref.close();
  }
}
