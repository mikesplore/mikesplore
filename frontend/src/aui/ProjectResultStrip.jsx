export default function ProjectResultStrip({ projects = [], links = [], onProjectClick, onLinkClick }) {
  return (
    <section className="w-full max-w-2xl" aria-label="Portfolio results">
      {projects.length > 0 && <>
        <p className="mb-3 px-0.5 text-xs font-medium text-muted">Projects</p>
        <div className="grid gap-3 sm:grid-cols-2" role="list">
          {projects.map((project) => <button
            key={project.id || project.url || project.title}
            type="button"
            onClick={() => onProjectClick?.(project)}
            className="w-full overflow-hidden rounded-2xl border border-divider bg-card text-left shadow-sm transition hover:-translate-y-0.5 hover:border-primary hover:shadow-md focus:outline-none focus:ring-2 focus:ring-accent"
            role="listitem"
          >
            <div className="flex h-28 items-center justify-center bg-elevated text-3xl text-muted" aria-hidden="true">
              {project.imageUrl ? <img src={project.imageUrl} alt="" className="h-full w-full object-cover" /> : '▣'}
            </div>
            <div className="p-4">
              <div className="flex items-start justify-between gap-3"><p className="font-semibold text-ink">{project.title}</p><span className="shrink-0 text-xs text-nav">Open ↗</span></div>
              {project.summary && <p className="mt-2 line-clamp-2 text-xs leading-5 text-muted">{project.summary}</p>}
            </div>
          </button>)}
        </div>
      </>}

      {links.length > 0 && <div className="mt-5">
        <p className="mb-3 px-0.5 text-xs font-semibold uppercase tracking-[0.18em] text-muted">Related links</p>
        <div className="space-y-2">
          {links.map((link) => <a key={link.url || link.label} href={link.url} target="_blank" rel="noreferrer" onClick={() => onLinkClick?.(link)} className="flex items-center gap-3 rounded-xl border border-divider bg-card px-3.5 py-3 text-sm font-medium text-ink transition hover:border-primary">
            {link.imageUrl && <img src={link.imageUrl} alt="" className="h-10 w-10 rounded-lg object-cover" />}<span className="min-w-0 flex-1"><span className="block truncate">{link.label}</span>{link.summary && <span className="mt-0.5 block truncate text-xs font-normal text-muted">{link.summary}</span>}</span><span className="shrink-0 text-xs text-nav">Open ↗</span>
          </a>)}
        </div>
      </div>}
    </section>
  );
}
