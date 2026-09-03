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
