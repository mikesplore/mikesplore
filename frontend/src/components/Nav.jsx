import { useRef } from 'react';
import { useEffect, useState } from 'react';
import { NavLink } from 'react-router-dom';
import { fetchCounts } from '../lib/portfolioApi';

const navItems = (counts) => [
  { to: '/', label: 'About', end: true },
  {
    to: '/projects',
    label: 'Projects',
    end: false,
    count: counts.projects,
  },
  { to: '/timeline', label: 'Timeline', end: false },
  { to: '/hackathons', label: 'Hackathons', end: false, count: counts.hackathons },
  { to: '/certificates', label: 'Certificates', end: false, count: counts.certificates },
  { to: '/events', label: 'Events', end: false, count: counts.events },
  { to: '/bucket-list', label: 'Bucket list', end: false, count: counts.bucket_list },
  { to: '/contact', label: 'Contact', end: false },
  { to: '/cv', label: 'CV', end: false },
];

const Nav = () => {
  const scrollContainerRef = useRef(null);
  const [counts, setCounts] = useState({});
  useEffect(() => { const controller = new AbortController(); fetchCounts(controller.signal).then(setCounts).catch(() => {}); return () => controller.abort(); }, []);

  const handleWheelScroll = (event) => {
    const container = scrollContainerRef.current;
    if (!container) return;

    const isOverflowing = container.scrollWidth > container.clientWidth;
    if (!isOverflowing) return;

    if (Math.abs(event.deltaY) > Math.abs(event.deltaX)) {
      container.scrollLeft += event.deltaY;
      event.preventDefault();
    }
  };

  return (
    <nav className="w-full border-b border-divider" aria-label="Main">
      <div
        ref={scrollContainerRef}
        onWheel={handleWheelScroll}
        className="scroll-pills -mx-5 overflow-x-auto px-5 sm:-mx-6 sm:px-6"
      >
        <ul className="flex w-max items-end gap-1">
          {navItems(counts).map((item) => (
            <li key={item.to} className="shrink-0">
              <NavLink
                to={item.to}
                end={item.end}
                className={({ isActive }) =>
                  `inline-block px-3 py-3 text-base transition-colors border-b-2 -mb-px ${
                    isActive
                      ? 'border-nav text-nav font-semibold'
                      : 'border-transparent text-muted hover:text-ink'
                  }`
                }
              >
                <span className="inline-flex items-center gap-1.5 whitespace-nowrap">
                  {item.label}
                  {item.count != null && (
                    <span
                      className="rounded-full bg-elevated px-1.5 py-0.5 text-xs tabular-nums text-subtle"
                      aria-label={`${item.count} ${item.label.toLowerCase()}`}
                    >
                      {item.count}
                    </span>
                  )}
                </span>
              </NavLink>
            </li>
          ))}
        </ul>
      </div>
    </nav>
  );
};

export default Nav;
