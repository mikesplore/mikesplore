import { ExternalLink, MapPin } from 'lucide-react';
import { events } from '../data/events';
import GalleryGrid from '../components/GalleryGrid';

const Events = () => {
  return (
    <ul className="divide-y divide-divider rounded-xl bg-elevated overflow-hidden">
      {events.map((event) => (
        <li key={`${event.title}-${event.date}`} className="p-4 sm:p-5">
          <div className={`flex gap-4 ${event.image ? '' : ''}`}>
            {event.image && (
              <a
                href={event.image}
                target="_blank"
                rel="noopener noreferrer"
                className="shrink-0"
              >
                <img
                  src={event.image}
                  alt=""
                  className="h-20 w-20 rounded-lg object-cover sm:h-24 sm:w-24"
                  loading="lazy"
                />
              </a>
            )}

            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
                <h2 className="text-base font-medium text-ink">{event.title}</h2>
                <span className="text-sm text-subtle">
                  {new Date(event.date + 'T00:00:00').toLocaleDateString('en-US', {
                    month: 'short',
                    year: 'numeric',
                  })}
                </span>
              </div>

              {event.location && (
                <p className="mt-1 inline-flex items-center gap-1.5 text-sm text-subtle">
                  <MapPin className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
                  {event.location}
                </p>
              )}

              <p className="mt-1 text-base leading-relaxed text-muted">{event.blurb}</p>

              {event.link && (
                <a
                  href={event.link}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="mt-2 inline-flex items-center gap-1.5 text-sm font-medium text-accent hover:text-accent/80"
                >
                  Event link
                  <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
                </a>
              )}

              {/* Photo gallery for this event */}
              {event.photos && event.photos.length > 0 && (
                <GalleryGrid photos={event.photos} eventId={event.id || event.title} />
              )}
            </div>
          </div>
        </li>
      ))}
    </ul>
  );
};

export default Events;
