import { oneLine, writeEntries } from './utils.js';

const USERNAME = 'mikesplore';

const response = await fetch(
  `https://dev.to/api/articles?username=${USERNAME}&per_page=30`
);

if (!response.ok) {
  throw new Error(`dev.to fetch failed: ${response.status} ${response.statusText}`);
}

const articles = await response.json();

const entries = articles.map((article) => ({
  date: article.published_at.split('T')[0],
  type: 'articles',
  title: article.title,
  blurb: oneLine(article.description) || 'Dev.to article',
  link: article.url,
  tags: (article.tag_list || []).slice(0, 5),
}));

writeEntries('entries.devto.json', entries);
