import { bootstrapApplication } from '@angular/platform-browser';
import { appConfig } from './app/app.config';
import { App } from './app/app';
import { setApiBase } from './app/core/label.service';

async function loadConfig(): Promise<void> {
  // A user-set override (via the in-app Config dialog) wins over config.json,
  // so a deployed build can be repointed at runtime without a rebuild.
  const override = localStorage.getItem('apiBase');
  if (override) {
    setApiBase(override);
    return;
  }
  try {
    const res = await fetch(new URL('config.json', document.baseURI), { cache: 'no-cache' });
    if (res.ok) setApiBase((await res.json())?.apiBase);
  } catch {
    // no config.json → keep the built-in default API base
  }
}

loadConfig().finally(() => {
  bootstrapApplication(App, appConfig).catch((err) => console.error(err));
});
