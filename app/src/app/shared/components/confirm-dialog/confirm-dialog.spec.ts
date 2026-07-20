import { TestBed } from '@angular/core/testing';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { ConfirmDialog } from './confirm-dialog';

describe('ConfirmDialog', () => {
  it('renders the message and closes with true/false', async () => {
    let closed: boolean | undefined;
    await TestBed.configureTestingModule({
      imports: [ConfirmDialog],
      providers: [
        { provide: MAT_DIALOG_DATA, useValue: { title: 'Delete', message: 'Sure?', confirmLabel: 'Delete' } },
        { provide: MatDialogRef, useValue: { close: (v: boolean) => (closed = v) } },
      ],
    }).compileComponents();

    const fixture = TestBed.createComponent(ConfirmDialog);
    fixture.detectChanges();
    expect((fixture.nativeElement as HTMLElement).textContent).toContain('Sure?');

    fixture.componentInstance.confirm();
    expect(closed).toBe(true);
    fixture.componentInstance.cancel();
    expect(closed).toBe(false);
  });
});
