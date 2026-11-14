const { chromium } = require('playwright-core');
const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');

const site = path.resolve('site');
const types = { '.html': 'text/html', '.css': 'text/css', '.mjs': 'text/javascript', '.png': 'image/png', '.jpg': 'image/jpeg' };
const server = http.createServer((req, res) => {
  const pathname = new URL(req.url, 'http://localhost').pathname;
  const file = path.resolve(site, '.' + (pathname === '/' ? '/index.html' : pathname));
  if (!file.startsWith(site + path.sep)) { res.writeHead(403).end(); return; }
  fs.readFile(file, (err, data) => { if (err) { res.writeHead(404).end(); return; } res.writeHead(200, { 'Content-Type': types[path.extname(file)] || 'application/octet-stream' }).end(data); });
});

(async () => {
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const browser = await chromium.launch({ executablePath: process.env.CHROME_PATH, headless: true, args: ['--no-sandbox'] });
  try {
    for (const [name, width, height] of [['desktop', 1440, 1000], ['mobile', 390, 844]]) {
      const page = await browser.newPage({ viewport: { width, height } });
      const errors = []; page.on('pageerror', error => errors.push(error.message));
      await page.route('https://api.github.com/repos/MatronixOwner/MatroOS/releases?per_page=100', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([
        { name: 'MatroOS test release', tag_name: 'test', draft: false, prerelease: true, published_at: '2026-10-25T00:00:00Z', html_url: 'https://github.com/MatronixOwner/MatroOS/releases/tag/test', assets: [{ name: 'test.iso', size: 1550000000, browser_download_url: 'https://github.com/MatronixOwner/MatroOS/releases/download/test/test.iso' }] }
      ]) }));
      await page.goto(`http://127.0.0.1:${server.address().port}/`, { waitUntil: 'networkidle' });
      assert.equal(await page.locator('#hero-download').getAttribute('href'), 'https://github.com/MatronixOwner/MatroOS/releases/download/test/test.iso');
      assert.equal(await page.locator('#release-name').innerText(), 'MatroOS test release');
      assert.equal(await page.locator('#start, a[href="#start"]').count(), 0);
      assert.equal(await page.getByText('Создай виртуальную машину').count(), 0);
      assert.match(await page.locator('.release-caution').innerText(), /без установщика на диск и сохранения данных/);
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true, `${name}: horizontal overflow`);
      assert.deepEqual(errors, []);
      fs.mkdirSync('site-test-output', { recursive: true });
      await page.screenshot({ path: `site-test-output/${name}.png`, fullPage: true });
      await page.close();
    }
  } finally { await browser.close(); server.close(); }
})().catch(error => { console.error(error); server.close(); process.exitCode = 1; });
