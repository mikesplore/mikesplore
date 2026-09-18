export default function ProjectResultStrip({ projects = [], links = [], onProjectClick, onLinkClick }) {
  return (
    <section className="w-full max-w-sm" aria-label="Portfolio results">
      {projects.length > 0 && <>
        <p className="mb-3 px-0.5 text-xs font-medium text-muted">Projects</p>
        <div className="flex snap-x gap-2 overflow-x-auto pb-1" role="list">
          {projects.map((project) => <button
            key={project.id || project.url || project.title}
            type="button"
            onClick={() => onProjectClick?.(project)}
            className="w-40 shrink-0 snap-start overflow-hidden rounded-2xl border border-divider bg-card text-left transition hover:border-primary focus:outline-none focus:ring-2 focus:ring-accent"
            role="listitem"
          >
            <div className="flex h-24 items-center justify-center bg-elevated text-muted" aria-hidden="true">
              {project.imageUrl ? <img src={project.imageUrl} alt="" className="h-full w-full object-cover" /> : '▣'}
            </div>
            <div className="p-2.5">
              <p className="truncate text-sm font-semibold text-ink">{project.title}</p>
              {project.summary && <p className="mt-0.5 truncate text-xs text-muted">{project.summary}</p>}
            </div>
          </button>)}
        </div>
      </>}

      {links.length > 0 && <div className="mt-5">
        <p className="mb-3 px-0.5 text-xs font-medium text-muted">Links</p>
        <div className="space-y-2">
          {links.map((link) => <a key={link.url || link.label} href={link.url} target="_blank" rel="noreferrer" onClick={() => onLinkClick?.(link)} className="flex items-center justify-between rounded-xl border border-divider bg-card px-3.5 py-3 text-sm font-medium text-ink transition hover:border-primary">
            <span className="truncate">{link.label}</span><span className="ml-3 shrink-0 text-xs text-nav">Open ↗</span>
          </a>)}
        </div>
      </div>}
    </section>
  );
}
