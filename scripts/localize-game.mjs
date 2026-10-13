const escapePattern = value => value.replace(/[/\\^$*+?.()|[\]{}]/g, '\\$&');

/** Render a locale without network access or browser-side translation. */
export function localizeGame(source, translations, { locale = 'zh', target = 'edu' } = {}) {
  if (!['zh', 'en'].includes(locale)) throw new Error('Unknown locale: ' + locale);
  const targets = {
    edu: { origin: 'https://edu.alading.org', zh: '/games/shotgun/', en: '/en/games/shotgun/' },
    standalone: { origin: 'https://alading.org', zh: '/shotgun/', en: '/shotgun/en/' },
  };
  const routes = targets[target];
  if (!routes) throw new Error('Unknown deployment target: ' + target);
  let html = source;
  if (locale === 'en') {
    for (const [key, value] of Object.entries(translations)) {
      if (!key || typeof value !== 'string' || /["'\\<>]/.test(value)) {
        throw new Error('Translation must be safe in HTML and JavaScript: ' + key);
      }
    }
    const pattern = Object.keys(translations).sort((a, b) => b.length - a.length).map(escapePattern).join('|');
    html = html.replace(new RegExp(pattern, 'gu'), match => translations[match]);
    const remaining = html.match(/[^\n]*\p{Script=Han}[^\n]*/gu);
    if (remaining) throw new Error('Untranslated source: ' + remaining.join('\n'));
    html = html.replace('<html lang="zh-CN">', '<html lang="en">');
  }
  html = html.replace(/(<link rel="canonical" href=")[^"]+/, '$1' + routes.origin + routes[locale]);
  for (const [code, language] of [['zh', 'zh-CN'], ['en', 'en']]) {
    html = html.replace(new RegExp('(<link rel="alternate" hreflang="' + language + '" href=")[^"]+'), '$1' + routes.origin + routes[code]);
  }
  const directory = (target === 'edu' ? '' : 'https://edu.alading.org') + (locale === 'en' ? '/en/games/' : '/games/');
  html = html.replace(/(id="games-link" href=")[^"]+/, '$1' + directory);
  const other = locale === 'en' ? 'zh' : 'en';
  const lang = other === 'zh' ? 'zh-CN' : 'en';
  html = html.replace(/<a id="language-link"[^>]*>[^<]*<\/a>/,
    '<a id="language-link" href="' + routes[other] + '" lang="' + lang + '" hreflang="' + lang + '">' + (other === 'en' ? 'English' : '中文') + '</a>');
  return html;
}
