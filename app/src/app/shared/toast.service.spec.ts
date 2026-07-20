import { TestBed } from '@angular/core/testing';
import { MatSnackBar } from '@angular/material/snack-bar';
import { ToastService } from './toast.service';

describe('ToastService', () => {
  it('opens success and error snackbars with the right panel classes', () => {
    const calls: unknown[][] = [];
    TestBed.configureTestingModule({
      providers: [{ provide: MatSnackBar, useValue: { open: (...a: unknown[]) => calls.push(a) } }],
    });
    const svc = TestBed.inject(ToastService);

    svc.success('done');
    svc.error('oops');

    expect(calls.length).toBe(2);
    expect(calls[0][0]).toBe('done');
    expect((calls[0][2] as { panelClass: string }).panelClass).toBe('toast-success');
    expect((calls[1][2] as { panelClass: string }).panelClass).toBe('toast-error');
  });
});
