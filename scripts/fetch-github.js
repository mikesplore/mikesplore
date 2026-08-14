import { oneLine, writeEntries } from './utils.js';

const USERNAME = 'mikesplore';

const PROJECT_REPOS = new Set([
  'vela',
  'vela-android',
  'vela-chat',
  'velavps',
  'VelaAI',
  'FarmPulse',
  'Kipepeo-Intelligence',
  'tessera',
  'apitemplate',
  'quickscore',
  'Timetable-Frontend',
  'Tuya',
  'quizbase',
  'StoryLoom',
  'style-ai-studio',
  'MyKeja',
  'Uni-Connect',
  'gatekeeperd',
]);

const HOBBY_REPOS = new Set([
  'github-wrapped',
  'EehSawa',
  'LinuxAutomation',
  'sentinel',
  'KenTube',
  'tutorai',
  'AnimalQuiz',
  'PC-Controller',
]);

const ALLOWED_FORKS = new Set([
  'dyad',
  'afara-dada-code',
  'zawadi-tunu'
]);

const CUSTOM_OVERRIDES = new Map([
  ['gatekeeperd', {
    blurb: 'Automatically blocks client websites when payment due has passed, and manage paid projects.',
    link: 'https://gatekeeperd.mikesplore.me',
  }],
]);

const INCLUDED_REPOS = new Map(
  [...PROJECT_REPOS].map((name) => [name.toLowerCase(), 'project'])
    .concat([...HOBBY_REPOS].map((name) => [name.toLowerCase(), 'hobby']))
    .concat([...ALLOWED_FORKS].map((name) => [name.toLowerCase(), 'project']))
);

const response = await fetch(
  `https://api.github.com/users/${USERNAME}/repos?sort=created&per_page=150`,
  {
    headers: {
      Accept: 'application/vnd.github+json',
      'User-Agent': 'mikesplore-portfolio',
    },
  }
);

if (!response.ok) {
  throw new Error(`GitHub fetch failed: ${response.status} ${response.statusText}`);
}

const repos = await response.json();

const entries = repos
  .filter((repo) => {
    const nameLower = repo.name.toLowerCase();
    const isMatched = INCLUDED_REPOS.has(nameLower);
    const isAllowedRepo = !repo.fork || ALLOWED_FORKS.has(nameLower);
    
    return isMatched && isAllowedRepo;
  })
  .map((repo) => {
    const type = INCLUDED_REPOS.get(repo.name.toLowerCase());
    const tags = [repo.language].filter(Boolean);
    const override = CUSTOM_OVERRIDES.get(repo.name.toLowerCase());

    return {
      date: repo.created_at.split('T')[0],
      type,
      title: repo.name.replace(/-/g, ' '),
      blurb: override?.blurb || oneLine(repo.description) || 'GitHub repository',
      link: override?.link || repo.html_url,
      tags,
    };
  });

writeEntries('entries.github.json', entries);
console.log(`Successfully filtered and saved ${entries.length} repos to portfolio!`);