// 동적으로 렌더링되는 시작 화면만 Playwright로 보완 저장한다.
import fs from 'node:fs/promises';
import path from 'node:path';
import { chromium } from 'playwright';

const output = process.env.DATA_ROOT || '/data';
const maxFiles = Number(process.env.MAX_FILES || 20);
const sources = {
  fsc: 'https://www.fsc.go.kr/', fss: 'https://www.fss.or.kr/', dart: 'https://dart.fss.or.kr/',
  krx: 'https://www.krx.co.kr/', ksd: 'https://www.ksd.or.kr/', nts: 'https://www.nts.go.kr/',
};
async function countText(dir) { let total = 0; for (const entry of await fs.readdir(dir, { withFileTypes: true }).catch(() => [])) total += entry.isDirectory() ? await countText(path.join(dir, entry.name)) : Number(entry.name.endsWith('.txt')); return total; }
let saved = await countText(output);
const browser = await chromium.launch({ headless: true });
for (const [name, startUrl] of Object.entries(sources)) {
  const queue = [{ url: startUrl, depth: 0 }], seen = new Set();
  const origin = new URL(startUrl).origin;
  let number = 0;
  while (queue.length && saved < maxFiles) {
    const { url, depth } = queue.shift();
    if (seen.has(url)) continue; seen.add(url);
    const page = await browser.newPage();
    try {
      await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 45_000 });
      const text = (await page.locator('body').innerText()).replace(/\s+/g, ' ').trim();
      if (text) { const directory = path.join(output, name, 'rendered'); await fs.mkdir(directory, { recursive: true }); await fs.writeFile(path.join(directory, `${String(++number).padStart(4, '0')}.txt`), `URL: ${page.url()}\n\n${text}\n`, 'utf8'); saved++; }
      if (depth < 2) for (const href of await page.locator('a[href]').evaluateAll(links => links.map(link => link.href))) if (href.startsWith(origin)) queue.push({ url: href, depth: depth + 1 });
    } catch (error) { console.error(`${name}: ${error.message}`); } finally { await page.close(); }
  }
  if (saved >= maxFiles) break;
}
await browser.close();
