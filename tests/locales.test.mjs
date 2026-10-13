import assert from 'node:assert/strict';
import test from 'node:test';
import { readFile } from 'node:fs/promises';
import { renderGame } from '../scripts/render-game.mjs';
import { localizeGame } from '../scripts/localize-game.mjs';

for (const target of ['edu', 'standalone']) {
  test(target + ' has complete locales and reciprocal navigation', async () => {
    for (const locale of ['zh', 'en']) {
      const html = await renderGame({ locale, target });
      const prefix = target === 'edu' ? 'https://edu.alading.org' : 'https://alading.org';
      const paths = target === 'edu' ? {zh:'/games/shotgun/',en:'/en/games/shotgun/'} : {zh:'/shotgun/',en:'/shotgun/en/'};
      assert.ok(html.includes('rel="canonical" href="' + prefix + paths[locale] + '"'));
      assert.ok(html.includes('id="language-link" href="' + paths[locale === 'en' ? 'zh' : 'en'] + '"'));
      assert.ok(html.includes('id="games-link" href="' + (target === 'edu' ? '' : 'https://edu.alading.org') + (locale === 'en' ? '/en/games/' : '/games/') + '"'));
      if (locale === 'en') assert.doesNotMatch(html.replace('中文', ''), /\p{Script=Han}/u);
      assert.equal((html.match(/id="lab"/g) || []).length, 1);
    }
  });
}
test('missing and unsafe translations fail before a page is served', async () => {
  const source = await readFile(new URL('../index.html', import.meta.url), 'utf8');
  assert.throws(() => localizeGame(source, {}, {locale:'en'}), /Untranslated source/);
  assert.throws(() => localizeGame(source, {'学习游戏':"Learn 'games'"}, {locale:'en'}), /Translation must be safe/);
  assert.throws(() => localizeGame(source, {}, {locale:'fr'}), /Unknown locale/);
  assert.throws(() => localizeGame(source, {}, {target:'unknown'}), /Unknown deployment target/);
});
