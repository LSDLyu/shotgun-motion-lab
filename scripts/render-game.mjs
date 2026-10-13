import { readFile } from 'node:fs/promises';
import { Script } from 'node:vm';
import { localizeGame } from './localize-game.mjs';

export async function renderGame(options = {}) {
  const [source, dictionary] = await Promise.all([
    readFile(new URL('../index.html', import.meta.url), 'utf8'),
    readFile(new URL('../locales/en.json', import.meta.url), 'utf8'),
  ]);
  const html = localizeGame(source, JSON.parse(dictionary), options);
  for (const [, script] of html.matchAll(/<script>([\s\S]*?)<\/script>/g)) new Script(script);
  return html;
}
