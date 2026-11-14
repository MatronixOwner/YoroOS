import { test } from 'node:test';
import assert from 'node:assert/strict';
import { usableReleases, releaseMeta, showReleases, loadReleases } from '../site/app.mjs';

const url = 'https://github.com/MatronixOwner/YoroOS/releases/download/';
const item = (tag, published, attrs = {}) => ({ name: tag, tag_name: tag, draft: false, prerelease: true,
  published_at: published, html_url: `https://github.com/MatronixOwner/YoroOS/releases/tag/${tag}`,
  assets: [{ name: `${tag}.iso`, size: 1073741824, browser_download_url: `${url}${tag}/${tag}.iso` }], ...attrs });

function fakeDoc() {
  const nodes = new Map();
  const make = () => ({ href: '', textContent: '', hidden: false, children: [],
    replaceChildren() { this.children = []; }, append(...children) { this.children.push(...children); }, setAttribute() {} });
  return { nodes, getElementById(id) { if (!nodes.has(id)) nodes.set(id, make()); return nodes.get(id); }, createElement: make };
}

test('only published ISO assets from this repository are selected and sorted by publication date', () => {
  const newer = item('new', '2026-02-02T00:00:00Z');
  const old = item('old', '2026-01-01T00:00:00Z');
  const draft = item('draft', '2027-01-01T00:00:00Z', { draft: true });
  const malware = item('bad', '2028-01-01T00:00:00Z', { assets: [{ name: 'bad.iso', browser_download_url: 'https://evil.example/bad.iso' }] });
  const noIso = item('noiso', '2029-01-01T00:00:00Z', { assets: [{ name: 'SHA256SUMS.txt', browser_download_url: url + 'x' }] });
  assert.deepEqual(usableReleases([old, draft, malware, newer, noIso]).map(x => x.tag_name), ['new', 'old']);
  assert.deepEqual(usableReleases({ message: 'rate limit' }), []);
  assert.match(releaseMeta(usableReleases([newer])[0]), /1,00 ГБ/);
});

test('updates both download links and creates safe release rows', () => {
  const doc = fakeDoc();
  const releases = usableReleases([item('old', '2026-01-01'), item('new', '2026-02-01')]);
  showReleases(releases, doc);
  assert.equal(doc.getElementById('hero-download').href, `${url}new/new.iso`);
  assert.equal(doc.getElementById('release-download').href, `${url}new/new.iso`);
  assert.equal(doc.getElementById('release-name').textContent, 'new');
  assert.equal(doc.getElementById('release-list').children[0].href, `${url}old/old.iso`);
});

test('retains fallback link if GitHub API is unavailable', async () => {
  const doc = fakeDoc(); doc.getElementById('hero-download').href = 'known-good';
  const original = globalThis.fetch; globalThis.fetch = async () => { throw new Error('offline'); };
  try { await loadReleases(doc); } finally { globalThis.fetch = original; }
  assert.equal(doc.getElementById('hero-download').href, 'known-good');
  assert.equal(doc.getElementById('release-list-fallback').hidden, false);
});
