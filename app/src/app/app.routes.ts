import { Routes } from '@angular/router';

export const routes: Routes = [
  { path: '', redirectTo: 'labeling', pathMatch: 'full' },
  { path: 'labeling', loadComponent: () => import('./labeling/labeling').then((m) => m.Labeling) },
  { path: 'data', loadComponent: () => import('./data/data').then((m) => m.Data) },
  { path: 'ocr', loadComponent: () => import('./ocr/ocr').then((m) => m.Ocr) },
];
