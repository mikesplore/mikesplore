import { useEffect, useMemo, useState } from 'react';
import { ENTRY_TYPES } from '../../data/types';
import { fetchTimelineEntries } from '../../lib/portfolioApi';
import TypeFilter from './TypeFilter';
import TimelineRow from './TimelineRow';

const TimelineFeed = () => {
  const [activeType, setActiveType] = useState(null);
  const [expandedKey, setExpandedKey] = useState(null);
  const [entries, setEntries] = useState([]);
  const [status, setStatus] = useState('loading');

  useEffect(() => {
    const controller = new AbortController();
    fetchTimelineEntries(controller.signal)
      .then((items) => {
        setEntries(items);
        setStatus('ready');
      })
      .catch((error) => {
        if (error.name !== 'AbortError') setStatus('error');
      });
    return () => controller.abort();
  }, []);

  const counts = useMemo(() => {
    return ENTRY_TYPES.reduce((acc, type) => {
      acc[type] = entries.filter((entry) => entry.type === type).length;
      return acc;
    }, {});
  }, [entries]);

  const filteredEntries = useMemo(() => {
    if (!activeType) return entries;
    return entries.filter((entry) => entry.type === activeType);
  }, [activeType, entries]);

  const getEntryKey = (entry) => `${entry.date}-${entry.title}`;

  const handleToggle = (key) => {
    setExpandedKey((current) => (current === key ? null : key));
  };

  return (
    <section aria-label="Timeline">
      <TypeFilter activeType={activeType} onChange={setActiveType} counts={counts} />

      <div className="mt-5">
        {status === 'loading' ? (
          <p className="py-8 text-center text-base text-subtle">Loading timeline…</p>
        ) : status === 'error' ? (
          <p className="py-8 text-center text-base text-subtle">Timeline is temporarily unavailable.</p>
        ) : filteredEntries.length === 0 ? (
          <p className="py-8 text-center text-base text-subtle">
            No {activeType ? `${activeType} ` : ''}entries yet.
          </p>
        ) : (
          <div className="rounded-xl bg-elevated overflow-hidden">
            {filteredEntries.map((entry) => {
              const key = getEntryKey(entry);
              return (
                <TimelineRow
                  key={key}
                  entry={entry}
                  isExpanded={expandedKey === key}
                  onToggle={() => handleToggle(key)}
                />
              );
            })}
          </div>
        )}
      </div>
    </section>
  );
};

export default TimelineFeed;
