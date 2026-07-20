import { Component, inject } from '@angular/core';
import { MAT_DIALOG_DATA, MatDialog, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { LabelService, Sample } from '../../core/label.service';
import { ToastService } from '../../shared/toast.service';
import { ConfirmDialog } from '../../shared/components/confirm-dialog/confirm-dialog';
import { ImageZoom } from './image-zoom';

@Component({
  selector: 'app-sample-detail',
  imports: [MatDialogModule, MatButtonModule, MatIconModule],
  templateUrl: './sample-detail.html',
  styleUrl: './sample-detail.scss',
})
export class SampleDetail {
  private svc = inject(LabelService);
  private toast = inject(ToastService);
  private dialog = inject(MatDialog);
  private ref = inject<MatDialogRef<SampleDetail>>(MatDialogRef);

  sample = inject<Sample>(MAT_DIALOG_DATA);

  openZoom(): void {
    this.dialog.open(ImageZoom, {
      data: { url: this.imageUrl(), alt: `sample ${this.sample.id}` },
      maxWidth: '95vw',
      panelClass: 'image-zoom-panel',
    });
  }

  imageUrl(): string {
    return this.svc.imageUrl(this.sample.id);
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
            this.ref.close(true);
          },
          error: () => this.toast.error('Could not delete the sample.'),
        });
      });
  }

  close(): void {
    this.ref.close();
  }
}
