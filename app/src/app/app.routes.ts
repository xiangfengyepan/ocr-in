import { Routes } from '@angular/router';

export const routes: Routes = [
  { path: '', redirectTo: 'labeling', pathMatch: 'full' },
  { path: 'labeling', loadComponent: () => import('./labeling/labeling').then((m) => m.Labeling) },
  { path: 'data', loadComponent: () => import('./data/data').then((m) => m.Data) },
  { path: 'models', loadComponent: () => import('./models/models').then((m) => m.Models) },
  { path: 'training', loadComponent: () => import('./training/training').then((m) => m.Training) },
  { path: 'ocr', loadComponent: () => import('./ocr/ocr').then((m) => m.Ocr) },
  { path: 'review', loadComponent: () => import('./review/review').then((m) => m.Review) },
];
