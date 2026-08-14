import devtoEntries from './entries.devto.json';
import githubEntries from './entries.github.json';

const normalizeLink = (link) => {
  if (!link) return null;
  try {
    const url = new URL(link);
    return `${url.hostname}${url.pathname}`.replace(/\/$/, '').toLowerCase();
  } catch {
    return link.toLowerCase();
  }
};

const dedupeEntries = (entries) => {
  const seenLinks = new Set();
  const seenTitles = new Set();

  return entries.filter((entry) => {
    const linkKey = normalizeLink(entry.link);
    const titleKey = entry.title.toLowerCase();

    if (linkKey) {
      if (seenLinks.has(linkKey)) return false;
      seenLinks.add(linkKey);
      return true;
    }

    if (seenTitles.has(titleKey)) return false;
    seenTitles.add(titleKey);
    return true;
  });
};

/** @type {import('./types.js').TimelineEntry[]} */
export const entries = dedupeEntries([
  ...githubEntries.map((entry) => ({ ...entry, type: 'repo' })),
  ...devtoEntries,
]).sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime());
