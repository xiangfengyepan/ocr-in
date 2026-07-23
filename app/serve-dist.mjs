// Minimal dependency-free static server for the built Angular app, with SPA
// fallback (unknown routes -> index.html). Binds 0.0.0.0 so it's reachable over
// the tailnet. PORT env overrides the default 4400.
import { createServer } from 'node:http';
import { readFile, stat } from 'node:fs/promises';
import { extname, join, normalize } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = fileURLToPath(new URL('./dist/app/browser/', import.meta.url));
const PORT = Number(process.env.PORT) || 4400;
const TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript',
  '.css': 'text/css',
  '.json': 'application/json',
  '.ico': 'image/x-icon',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.svg': 'image/svg+xml',
  '.webp': 'image/webp',
  '.woff2': 'font/woff2',
  '.woff': 'font/woff',
  '.map': 'application/json',
  '.txt': 'text/plain; charset=utf-8',
};

async function resolveFile(urlPath) {
  const clean = decodeURIComponent(new URL(urlPath, 'http://x').pathname);
  let file = normalize(join(ROOT, clean));
  if (!file.startsWith(ROOT)) return null; // path traversal guard
  let s = await stat(file).catch(() => null);
  if (s && s.isDirectory()) {
    file = join(file, 'index.html');
    s = await stat(file).catch(() => null);
  }
  if (!s) file = join(ROOT, 'index.html'); // SPA fallback
  return file;
}

createServer(async (req, res) => {
  try {
    const file = await resolveFile(req.url || '/');
    if (!file) {
      res.writeHead(403);
      return res.end('forbidden');
    }
    const body = await readFile(file);
    // index.html + config.json must always revalidate (they point at the current
    // hashed bundles / API base); content-hashed assets can cache forever.
    const revalidate = extname(file) === '.html' || file.endsWith('config.json');
    res.writeHead(200, {
      'content-type': TYPES[extname(file)] || 'application/octet-stream',
      'cache-control': revalidate ? 'no-cache' : 'public, max-age=31536000, immutable',
    });
    res.end(body);
  } catch {
    res.writeHead(500);
    res.end('server error');
  }
}).listen(PORT, '0.0.0.0', () => console.log(`ocr-in frontend on http://0.0.0.0:${PORT}`));
