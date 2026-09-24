import { useEffect, useState } from 'react';
import { ExternalLink, Github } from 'lucide-react';
import { fetchProjects } from '../lib/portfolioApi';
import EmptyState from '../components/EmptyState';

const externalUrl = (value) => {
  try {
    const url = new URL(value);
    return ['http:', 'https:'].includes(url.protocol) ? url.href : null;
  } catch {
    return null;
  }
};

const Projects = () => {
  const [projects, setProjects] = useState([]);
  const [status, setStatus] = useState('loading');
  useEffect(() => {
    const controller = new AbortController();
    fetchProjects(controller.signal).then((items) => {
      setProjects(items.map((item) => ({ ...item, id: item.slug })));
      setStatus('ready');
    }).catch((error) => { if (error.name !== 'AbortError') setStatus('error'); });
    return () => controller.abort();
  }, []);
  if (status === 'loading') return <p className="py-8 text-center text-base text-subtle">Loading projects…</p>;
  if (status === 'error') return <p className="py-8 text-center text-base text-subtle">Projects are temporarily unavailable.</p>;
  if (projects.length === 0) return <EmptyState title="No projects to show yet">Projects will appear here once they are added to the portfolio.</EmptyState>;
  return (
    <ul className="divide-y divide-divider rounded-xl bg-elevated overflow-hidden">
      {projects.map((project) => {
        const repoUrl = externalUrl(project.links?.repo);
        const demoUrl = externalUrl(project.links?.demo);
        return (
        <li key={project.id}>
          <div className="group flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:gap-4 sm:p-5 transition-colors hover:bg-accent/5">
            <div className="h-36 w-full shrink-0 overflow-hidden rounded-lg bg-elevated sm:h-24 sm:w-24">
              <img
                src={
                  project.cardImage ||
                  `https://ui-avatars.com/api/?name=${encodeURIComponent(project.title)}`
                }
                alt={`${project.title} preview`}
                className="h-full w-full object-cover"
                loading="lazy"
              />
            </div>

            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
                <h2 className="text-base font-medium text-ink group-hover:text-teal transition-colors">
                  {project.title}
                </h2>
                <span className="text-xs text-subtle">{project.tagline}</span>
              </div>

              <p className="mt-1.5 text-sm leading-relaxed text-muted">{project.summary}</p>

              {(repoUrl || demoUrl) && (
                <div className="mt-1.5 flex flex-wrap items-center gap-3 text-xs font-medium">
                  {repoUrl && (
                    <a
                      href={repoUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 text-teal hover:opacity-80"
                      aria-label={`${project.title} GitHub repository`}
                    >
                      <Github className="h-3.5 w-3.5" aria-hidden="true" />
                      GitHub
                    </a>
                  )}
                  {demoUrl && (
                    <a
                      href={demoUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 text-accent hover:text-accent/80"
                      aria-label={`${project.title} live demo`}
                    >
                      <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
                      Live
                    </a>
                  )}
                </div>
              )}
            </div>
          </div>
        </li>
        );
      })}
    </ul>
  );
};

export default Projects;
