import { Routes } from '@angular/router';

export const routes: Routes = [
  { path: '', redirectTo: 'labeling', pathMatch: 'full' },
  { path: 'labeling', loadComponent: () => import('./labeling/labeling').then((m) => m.Labeling) },
  { path: 'ocr', loadComponent: () => import('./ocr/ocr').then((m) => m.Ocr) },
];
