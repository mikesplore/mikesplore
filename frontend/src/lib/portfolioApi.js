const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const content = (entry, key) => entry.content_blocks?.[key] || entry[key] || [];

export const normalizeEntry = (entry) => {
  const repositories = entry.repositories || [];
  const primaryRepository = repositories.find((repo) => repo.is_primary) || repositories[0];
  const links = entry.links || {};
  return { ...entry, summary: entry.summary || entry.blurb || '', tagline: entry.tagline || entry.subtitle || '', stack: entry.stack || entry.technologies || entry.tech_stack || [], links: { ...links, repo: links.repo || primaryRepository?.url, demo: links.demo || entry.demo_url }, cardImage: entry.card_image || entry.icon_url || entry.media?.image || entry.media?.thumbnail || '', topology: content(entry, 'topology'), metrics: content(entry, 'metrics'), highlights: content(entry, 'highlights'), documents: content(entry, 'documents') };
};

const toTimelineEntry = (rawEntry) => {
  const entry = normalizeEntry(rawEntry);
  return {
  date: entry.date || `${entry.year || new Date().getFullYear()}-01-01`,
  type: entry.content_type,
  title: entry.title,
  blurb: entry.blurb,
  link: entry.links?.url || entry.links?.external || entry.links?.repo || entry.links?.demo || '',
  tags: entry.tags || [],
  readTime: entry.details?.readTime ?? 0,
  stars: entry.details?.stars ?? 0,
  thumbnail: entry.media?.thumbnail || entry.media?.image || '',
  };
};

export async function fetchTimelineEntries(page = 1, signal) {
  const response = await fetch(`${API_BASE_URL}/entries?content_type=article&page=${page}&page_size=10`, { signal });
  if (!response.ok) throw new Error(`Portfolio API request failed (${response.status})`);
  const entries = await response.json();
  return { items: entries.map(toTimelineEntry), total: Number(response.headers.get('X-Total-Count') || entries.length) };
}

async function fetchJson(path, signal) {
  const response = await fetch(`${API_BASE_URL}${path}`, { signal });
  if (!response.ok) throw new Error(`Portfolio API request failed (${response.status})`);
  return response.json();
}

export function fetchBucketList(signal) {
  return fetchJson('/bucket-list', signal);
}

export function fetchProfileLinks(signal) {
  return fetchJson('/profile/links', signal);
}

export function fetchProfile(signal) {
  return fetchJson('/profile', signal);
}

export function fetchProjects(signal) {
  return fetchJson('/projects', signal).then((items) => items.map(normalizeEntry));
}

export function fetchProject(slug, signal) {
  return fetchJson(`/projects/${encodeURIComponent(slug)}`, signal).then(normalizeEntry);
}

export function fetchEntriesByType(type, signal) {
  return fetchJson(`/entries?content_type=${encodeURIComponent(type)}&page_size=50`, signal).then((items) => items.map(normalizeEntry));
}

export function fetchCertificates(signal) {
  return fetchJson('/certificates', signal);
}

export function fetchEducation(signal) {
  return fetchJson('/education', signal);
}

export function fetchCounts(signal) {
  return fetchJson('/counts', signal);
}

export function fetchAssets(signal) {
  return fetchJson('/assets', signal);
}
