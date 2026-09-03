import { mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { projectsCatalog } from '../src/data/projectsCatalog.js';
import { events } from '../src/data/events.js';
import { bucketListItems, bucketListMeta } from '../src/data/bucketList.js';
import { contactSocials, education, hackathons, skillsGrouped, socialLinks, status, availability } from '../src/data/profile.js';

const root = join(fileURLToPath(new URL('.', import.meta.url)), '../../backend/data');
mkdirSync(root, { recursive: true });
const content = { projects: projectsCatalog, events, bucketListItems, bucketListMeta, contactSocials, education, hackathons, skillsGrouped, socialLinks, status, availability };
for (const [name, value] of Object.entries(content)) writeFileSync(join(root, `${name}.json`), `${JSON.stringify(value, null, 2)}\n`);
console.log(`Exported ${Object.keys(content).length} content collections`);
