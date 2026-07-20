import { Component, inject } from '@angular/core';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';

@Component({
  selector: 'app-image-zoom',
  template: `<img [src]="data.url" [alt]="data.alt" (click)="ref.close()" />`,
  styles: `
    img {
      display: block;
      height: 85vh;
      width: auto;
      max-width: 92vw;
      object-fit: contain;
      margin: 0 auto;
      background: #fff;
      border-radius: 6px;
      cursor: zoom-out;
    }
  `,
})
export class ImageZoom {
  data = inject<{ url: string; alt: string }>(MAT_DIALOG_DATA);
  ref = inject<MatDialogRef<ImageZoom>>(MatDialogRef);
}
