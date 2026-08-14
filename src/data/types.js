/**
 * @typedef {"repo" | "articles"} EntryType
 */

/**
 * @typedef {Object} TimelineEntry
 * @property {string} date - ISO date, e.g. "2026-07-11"
 * @property {EntryType} type
 * @property {string} title
 * @property {string} blurb - one line
 * @property {string} [link] - external URL
 * @property {string[]} [tags]
 */

export const ENTRY_TYPES = ['repo', 'articles'];

export const TYPE_LABELS = {
  repo: 'GitHub',
  articles: 'Articles',
};
