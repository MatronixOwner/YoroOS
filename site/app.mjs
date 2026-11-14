const REPO = 'MatronixOwner/MatroOS';
const RELEASES = `https://api.github.com/repos/${REPO}/releases?per_page=100`;
const DOWNLOAD_PREFIX = `https://github.com/${REPO}/releases/download/`;
const RELEASE_PREFIX = `https://github.com/${REPO}/releases/tag/`;

export function usableReleases(value) {
  if (!Array.isArray(value)) return [];
  return value.filter(release => release && !release.draft && Array.isArray(release.assets))
    .map(release => {
      const iso = release.assets.find(asset => typeof asset?.name === 'string' && /\.iso$/i.test(asset.name)
        && typeof asset.browser_download_url === 'string' && asset.browser_download_url.startsWith(DOWNLOAD_PREFIX));
      return iso ? { ...release, iso } : null;
    }).filter(Boolean)
    .sort((a, b) => (Date.parse(b.published_at) || 0) - (Date.parse(a.published_at) || 0));
}

export function releaseMeta(release) {
  const bits = [];
  const date = new Date(release.published_at);
  if (!Number.isNaN(date.valueOf())) bits.push(new Intl.DateTimeFormat('ru-RU', { day: 'numeric', month: 'long', year: 'numeric', timeZone: 'UTC' }).format(date));
  if (Number.isFinite(release.iso?.size) && release.iso.size > 0) bits.push(`${(release.iso.size / 1024 ** 3).toFixed(2).replace('.', ',')} ГБ`);
  if (release.prerelease) bits.push('предварительный выпуск');
  return bits.join(' · ');
}

export function showReleases(releases, doc) {
  const latest = releases[0];
  doc.getElementById('hero-download').href = latest.iso.browser_download_url;
  doc.getElementById('release-download').href = latest.iso.browser_download_url;
  doc.getElementById('release-name').textContent = latest.name || latest.tag_name || 'MatroOS';
  doc.getElementById('release-meta').textContent = releaseMeta(latest) || 'Образ ISO';
  doc.getElementById('hero-version').textContent = latest.prerelease ? 'ПРЕДВАРИТЕЛЬНЫЙ ВЫПУСК' : 'АКТУАЛЬНЫЙ ВЫПУСК';
  doc.getElementById('release-status').textContent = 'Образы загружаются напрямую с GitHub Releases.';
  const list = doc.getElementById('release-list');
  list.replaceChildren();
  for (const release of releases.slice(1, 6)) {
    const row = doc.createElement('a');
    row.className = 'release-row';
    row.href = release.iso.browser_download_url;
    const title = doc.createElement('span'); title.className = 'release-row-name';
    title.textContent = release.name || release.tag_name || release.iso.name;
    const info = doc.createElement('span'); info.className = 'release-row-meta'; info.textContent = releaseMeta(release);
    const arrow = doc.createElement('span'); arrow.className = 'release-row-arrow'; arrow.setAttribute('aria-hidden', 'true'); arrow.textContent = '↗';
    row.append(title, info, arrow); list.append(row);
  }
  // The release-notes link is fixed to the verified repository, not arbitrary API HTML.
  const notes = doc.getElementById('release-notes');
  if (typeof latest.html_url === 'string' && latest.html_url.startsWith(RELEASE_PREFIX)) notes.href = latest.html_url;
}

export async function loadReleases(doc) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 8000);
  try {
    const response = await fetch(RELEASES, { signal: controller.signal, headers: { Accept: 'application/vnd.github+json' } });
    if (!response.ok) throw new Error(`GitHub ${response.status}`);
    const releases = usableReleases(await response.json());
    if (!releases.length) throw new Error('No published ISO');
    showReleases(releases, doc);
  } catch (_error) {
    doc.getElementById('release-status').textContent = 'Не удалось проверить обновления. Ниже доступен ранее опубликованный образ.';
    doc.getElementById('release-list-fallback').hidden = false;
  } finally { clearTimeout(timer); }
}

if (typeof document !== 'undefined') loadReleases(document);
