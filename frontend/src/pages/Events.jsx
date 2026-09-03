import { ExternalLink, MapPin } from 'lucide-react';
import { useEffect, useState } from 'react';
import GalleryGrid from '../components/GalleryGrid';
import { fetchEntriesByType } from '../lib/portfolioApi';

const Events = () => {
  const [events, setEvents] = useState([]);
  const [status, setStatus] = useState('loading');
  useEffect(() => {
    const controller = new AbortController();
    fetchEntriesByType('event', controller.signal).then((items) => {
      setEvents(items.map((item) => ({ title: item.title, date: item.date, blurb: item.blurb, location: item.details?.location, link: item.links?.url, image: item.media?.image, photos: item.media?.photos }))); setStatus('ready');
    }).catch((error) => { if (error.name !== 'AbortError') setStatus('error'); });
    return () => controller.abort();
  }, []);
  if (status === 'loading') return <p className="py-8 text-center text-base text-subtle">Loading events…</p>;
  if (status === 'error') return <p className="py-8 text-center text-base text-subtle">Events are temporarily unavailable.</p>;
  return (
    <ul className="divide-y divide-divider rounded-xl bg-elevated overflow-hidden">
      {events.map((event) => (
        <li key={`${event.title}-${event.date}`} className="p-4 sm:p-5">
          <div className="flex flex-col gap-3 sm:flex-row sm:gap-4">
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
                  className="h-36 w-full rounded-lg object-cover sm:h-24 sm:w-24"
                  loading="lazy"
                />
              </a>
            )}

            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
                <h2 className="text-base font-medium text-ink">{event.title}</h2>
                <span className="text-xs text-subtle">
                  {new Date(event.date + 'T00:00:00').toLocaleDateString('en-US', {
                    month: 'short',
                    year: 'numeric',
                  })}
                </span>
              </div>

              {event.location && (
                <p className="mt-1.5 inline-flex items-center gap-1.5 text-sm leading-relaxed text-subtle">
                  <MapPin className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
                  {event.location}
                </p>
              )}

              <p className="mt-2 text-base leading-relaxed text-muted">{event.blurb}</p>

              {event.link && (
                <a
                  href={event.link}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="mt-2.5 inline-flex items-center gap-1.5 text-sm font-medium text-accent hover:text-accent/80"
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
