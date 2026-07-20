import { Injectable, inject } from '@angular/core';
import { MatSnackBar } from '@angular/material/snack-bar';

@Injectable({ providedIn: 'root' })
export class ToastService {
  private snack = inject(MatSnackBar);

  success(message: string): void {
    this.snack.open(message, 'OK', {
      duration: 2500,
      panelClass: 'toast-success',
      horizontalPosition: 'right',
    });
  }

  error(message: string): void {
    this.snack.open(message, 'Dismiss', {
      duration: 5000,
      panelClass: 'toast-error',
      horizontalPosition: 'right',
    });
  }
}
