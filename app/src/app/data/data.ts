import { Component, OnInit, inject, signal } from '@angular/core';
import { LabelService, Rating, Sample } from '../core/label.service';

@Component({
  selector: 'app-data',
  templateUrl: './data.html',
  styleUrl: './data.scss',
})
export class Data implements OnInit {
  private svc = inject(LabelService);
  samples = signal<Sample[]>([]);

  ngOnInit(): void {
    this.reload();
  }

  reload(): void {
    this.svc.listSamples().subscribe((rows) => this.samples.set(rows));
  }

  imageUrl(id: number): string {
    return this.svc.imageUrl(id);
  }

  setText(s: Sample, value: string): void {
    s.text = value;
  }

  setRating(s: Sample, rating: Rating): void {
    s.rating = rating;
    this.samples.set([...this.samples()]);
  }

  save(s: Sample): void {
    this.svc.updateSample(s.id, { text: s.text, rating: s.rating }).subscribe();
  }

  remove(s: Sample): void {
    this.svc
      .deleteSample(s.id)
      .subscribe(() => this.samples.set(this.samples().filter((x) => x.id !== s.id)));
  }
}
