import { copyFile, mkdir } from 'node:fs/promises';

const assets = new URL('./assets/shotgun/', import.meta.url);
await mkdir(assets, { recursive: true });
await copyFile(new URL('../index.html', import.meta.url), new URL('index.html', assets));
console.log('Prepared Cloudflare assets from the canonical index.html.');
