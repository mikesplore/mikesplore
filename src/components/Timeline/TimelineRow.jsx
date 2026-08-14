import { ChevronDown, Clock, ExternalLink, Star } from 'lucide-react';
import EntryIcon from './EntryIcon';

const formatDate = (isoDate) => {
  const date = new Date(isoDate + 'T00:00:00');
  return date.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
};

const TimelineRow = ({ entry, isExpanded, onToggle }) => {
  const panelId = `timeline-panel-${entry.date}-${entry.title.replace(/\s+/g, '-').toLowerCase()}`;
  const thumbnail = entry.thumbnail || '';
  const stars = entry.stars ?? 0;
  const readTime = entry.readTime ?? 0;
  const language = entry.tags?.[0] || '';

  return (
    <div className="border-b border-divider last:border-b-0">
      <button
        type="button"
        onClick={onToggle}
        aria-expanded={isExpanded}
        aria-controls={panelId}
        className="grid w-full grid-cols-[5rem_1fr_auto_auto] items-center gap-3 px-4 py-4 text-left transition-colors hover:bg-[var(--color-hover)] sm:grid-cols-[4rem_1fr_auto_auto]"
      >
        {/* Thumbnail / icon */}
        <div className="h-14 w-20 shrink-0 overflow-hidden rounded-lg bg-elevated sm:h-12 sm:w-16">
          {thumbnail ? (
            <img
              src={thumbnail}
              alt=""
              className="h-full w-full object-cover"
              loading="lazy"
            />
          ) : (
            <div className="flex h-full w-full items-center justify-center">
              <EntryIcon title={entry.title} type={entry.type} link={entry.link} />
            </div>
          )}
        </div>

        <span className="min-w-0 flex-1">
          <span className="block truncate text-base font-medium text-ink">{entry.title}</span>
        </span>

        <span className="shrink-0 text-sm tabular-nums text-subtle">{formatDate(entry.date)}</span>

        <ChevronDown
          className={`h-5 w-5 shrink-0 text-subtle transition-transform ${isExpanded ? 'rotate-180' : ''}`}
          aria-hidden="true"
        />
      </button>

      {isExpanded && (
        <div id={panelId} className="border-t border-divider bg-card px-4 pb-5 pt-4">
          <div className="grid grid-cols-[5rem_1fr] gap-3 sm:grid-cols-[4rem_1fr]">
            {/* Spacer matching the thumbnail column */}
            <div aria-hidden="true" />

            <div>
              <p className="text-base leading-relaxed text-muted">{entry.blurb}</p>

              {/* Metadata */}
              {((entry.type === 'repo' && (stars > 0 || language)) ||
                (entry.type === 'articles' && readTime > 0)) && (
                <div className="mt-3 flex flex-wrap gap-3 text-sm text-subtle">
                    <span className="inline-flex items-center gap-1">
                      <Star className="h-3.5 w-3.5" aria-hidden="true" />
                      {stars} {stars === 1 ? 'star' : 'stars'}
                    </span>
                  )}
                  {entry.type === 'repo' && language && (
                    <span className="inline-flex items-center gap-1">
                      <span className="h-2 w-2 rounded-full bg-accent" aria-hidden="true" />
                      {language}
                    </span>
                  )}
                  {entry.type === 'articles' && readTime > 0 && (
                    <span className="inline-flex items-center gap-1">
                      <Clock className="h-3.5 w-3.5" aria-hidden="true" />
                      {readTime} min read
                    </span>
                  )}
                </div>
              )}

              {entry.tags && entry.tags.length > 0 && (
                <div className="mt-3 flex flex-wrap gap-2">
                  {entry.tags.map((tag) => (
                    <span key={tag} className="chip text-sm">
                      {tag}
                    </span>
                  ))}
                </div>
              )}

              <div className="mt-3 flex flex-wrap gap-4 text-base">
                {entry.link && (
                  <a
                    href={entry.link}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-muted hover:text-ink"
                  >
                    Visit
                    <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
                  </a>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default TimelineRow;