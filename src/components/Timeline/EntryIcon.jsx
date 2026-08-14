const TYPE_COLORS = {
  repo: 'bg-slate-500/20 text-slate-300',
  project: 'bg-amber-500/20 text-amber-300',
  hobby: 'bg-teal-500/20 text-teal-300',
  articles: 'bg-violet-500/20 text-violet-300',
  client: 'bg-sky-500/20 text-sky-300',
  talk: 'bg-emerald-500/20 text-emerald-300',
  now: 'bg-rose-500/20 text-rose-300',
};

const getDomain = (url) => {
  try {
    return new URL(url).hostname.replace(/^www\./, '');
  } catch {
    return null;
  }
};

const getInitials = (title) => {
  const words = title.trim().split(/\s+/).filter(Boolean);
  if (words.length === 0) return '?';
  if (words.length === 1) return words[0].slice(0, 2).toUpperCase();
  return (words[0][0] + words[1][0]).toUpperCase();
};

const EntryIcon = ({ title, type, link }) => {
  const domain = link ? getDomain(link) : null;
  const colorClass = TYPE_COLORS[type] || TYPE_COLORS.project;

  if (domain) {
    return (
      <img
        src={`https://www.google.com/s2/favicons?domain=${domain}&sz=64`}
        alt=""
        width={36}
        height={36}
        className="h-9 w-9 rounded-md bg-card object-contain p-1"
        loading="lazy"
      />
    );
  }

  return (
    <div
      className={`flex h-9 w-9 items-center justify-center rounded-md text-sm font-semibold ${colorClass}`}
      aria-hidden="true"
    >
      {getInitials(title)}
    </div>
  );
};

export default EntryIcon;
