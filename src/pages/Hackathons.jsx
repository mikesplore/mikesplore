import { ExternalLink } from 'lucide-react';
import { hackathons } from '../data/profile';

const resultStyles = {
  Participating: 'bg-teal-soft text-teal',
  Submitted: 'bg-accent-soft text-accent',
  Winner: 'bg-accent-soft text-accent',
  '#25': 'bg-elevated text-muted',
};

const getLinkLabel = (item) => {
  if (item.linkLabel) return item.linkLabel;
  if (item.result === 'Winner' || item.link?.includes('github.com')) return 'View project';
  if (item.result === 'Participating' || item.result === 'Submitted') return 'View hackathon';
  return 'View details';
};

const Hackathons = () => {
  return (
    <ul className="divide-y divide-divider rounded-xl bg-elevated overflow-hidden">
      {hackathons.map((item) => (
        <li key={`${item.title}-${item.year}`} className="p-4 sm:p-5">
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="text-base font-medium text-ink">{item.title}</h2>
            <span
              className={`rounded-full px-2.5 py-0.5 text-sm font-medium ${
                resultStyles[item.result] || resultStyles['#25']
              }`}
            >
              {item.result}
            </span>
            <span className="text-sm text-subtle">{item.year}</span>
          </div>

          {item.project && (
            <p className="mt-2 text-base font-medium text-muted">{item.project}</p>
          )}
          <p className="mt-1 text-base leading-relaxed text-muted">{item.description}</p>

          {item.organization && (
            <p className="mt-1 text-sm text-subtle">{item.organization}</p>
          )}

          {item.link && (
            <a
              href={item.link}
              target="_blank"
              rel="noopener noreferrer"
              className="mt-3 inline-flex items-center gap-1.5 text-base font-medium text-accent hover:text-accent/80"
            >
              {getLinkLabel(item)}
              <ExternalLink className="h-4 w-4" aria-hidden="true" />
            </a>
          )}
        </li>
      ))}
    </ul>
  );
};

export default Hackathons;
