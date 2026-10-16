import { mkdir, writeFile } from 'node:fs/promises';
import { renderGame } from '../scripts/render-game.mjs';

for (const locale of ['zh', 'en']) {
  const assets = new URL('./assets/shotgun/' + (locale === 'en' ? 'en/' : ''), import.meta.url);
  await mkdir(assets, { recursive: true });
  await writeFile(new URL('index.html', assets), await renderGame({ locale, target: 'standalone' }));
}
console.log('Prepared both Cloudflare locales from the canonical model and translations.');
