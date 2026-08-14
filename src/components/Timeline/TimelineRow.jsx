import { ChevronDown, ExternalLink } from 'lucide-react';
import EntryIcon from './EntryIcon';

const formatDate = (isoDate) => {
  const date = new Date(isoDate + 'T00:00:00');
  return date.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
};

const TimelineRow = ({ entry, isExpanded, onToggle }) => {
  const panelId = `timeline-panel-${entry.date}-${entry.title.replace(/\s+/g, '-').toLowerCase()}`;

  return (
    <div className="border-b border-divider last:border-b-0">
      <button
        type="button"
        onClick={onToggle}
        aria-expanded={isExpanded}
        aria-controls={panelId}
        className="flex w-full items-center gap-3 px-4 py-4 text-left transition-colors hover:bg-[var(--color-hover)]"
      >
        <EntryIcon title={entry.title} type={entry.type} link={entry.link} />

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
        <div id={panelId} className="border-t border-divider bg-card px-4 pb-5 pt-4 pl-16">
          <p className="text-base leading-relaxed text-muted">{entry.blurb}</p>

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
      )}
    </div>
  );
};

export default TimelineRow;
