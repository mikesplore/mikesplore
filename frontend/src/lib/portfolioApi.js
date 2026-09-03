const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const toTimelineEntry = (entry) => ({
  date: entry.date || `${entry.year || new Date().getFullYear()}-01-01`,
  type: entry.content_type,
  title: entry.title,
  blurb: entry.blurb,
  link: entry.links?.url || entry.links?.external || entry.links?.repo || entry.links?.demo || '',
  tags: entry.tags || [],
  readTime: entry.details?.readTime ?? 0,
  stars: entry.details?.stars ?? 0,
  thumbnail: entry.media?.thumbnail || entry.media?.image || '',
});

export async function fetchTimelineEntries(signal) {
  const response = await fetch(`${API_BASE_URL}/entries`, { signal });
  if (!response.ok) throw new Error(`Portfolio API request failed (${response.status})`);
  const entries = await response.json();
  return entries.map(toTimelineEntry);
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
  return fetchJson('/entries?content_type=project&page_size=50', signal);
}

export function fetchEntriesByType(type, signal) {
  return fetchJson(`/entries?content_type=${encodeURIComponent(type)}&page_size=50`, signal);
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
