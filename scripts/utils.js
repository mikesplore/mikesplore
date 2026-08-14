import { writeFileSync } from 'fs';
import { dirname, join } from 'path';
import { fileURLToPath } from 'url';

const rootDir = join(dirname(fileURLToPath(import.meta.url)), '..');

export const dataDir = join(rootDir, 'src/data');

export function writeEntries(filename, entries) {
  const path = join(dataDir, filename);
  writeFileSync(path, `${JSON.stringify(entries, null, 2)}\n`, 'utf8');
  console.log(`Wrote ${entries.length} entries to ${filename}`);
}

export function oneLine(text, max = 100) {
  const clean = (text || '').replace(/\s+/g, ' ').trim();
  if (!clean) return '';
  if (clean.length <= max) return clean;
  return `${clean.slice(0, max).replace(/\s+\S*$/, '')}…`;
}
