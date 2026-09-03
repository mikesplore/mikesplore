import { Link } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { ExternalLink, Github } from 'lucide-react';
import { fetchProjects } from '../lib/portfolioApi';

const Projects = () => {
  const [projects, setProjects] = useState([]);
  const [status, setStatus] = useState('loading');
  useEffect(() => {
    const controller = new AbortController();
    fetchProjects(controller.signal).then((items) => {
      setProjects(items.map((item) => ({ id: item.slug, title: item.title, summary: item.blurb, ...(item.details || {}), stack: item.tech_stack, tags: item.tags, links: item.links, ...(item.media || {}) })));
      setStatus('ready');
    }).catch((error) => { if (error.name !== 'AbortError') setStatus('error'); });
    return () => controller.abort();
  }, []);
  if (status === 'loading') return <p className="py-8 text-center text-base text-subtle">Loading projects…</p>;
  if (status === 'error') return <p className="py-8 text-center text-base text-subtle">Projects are temporarily unavailable.</p>;
  return (
    <ul className="divide-y divide-divider rounded-xl bg-elevated overflow-hidden">
      {projects.map((project) => (
        <li key={project.id}>
          <Link
            to={`/projects/${project.id}`}
            className="group flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:gap-4 sm:p-5 transition-colors hover:bg-accent/5"
          >
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

              {(project.links?.repo || project.links?.demo) && (
                <div className="mt-1.5 flex flex-wrap items-center gap-3 text-xs font-medium">
                  {project.links?.repo && (
                    <span
                      className="inline-flex items-center gap-1 text-teal hover:opacity-80"
                      onClick={(e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        window.open(project.links.repo, '_blank', 'noopener,noreferrer');
                      }}
                      role="link"
                      tabIndex={0}
                      aria-label={`${project.title} GitHub repository`}
                    >
                      <Github className="h-3.5 w-3.5" aria-hidden="true" />
                      GitHub
                    </span>
                  )}
                  {project.links?.demo && (
                    <span
                      className="inline-flex items-center gap-1 text-accent hover:text-accent/80"
                      onClick={(e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        window.open(project.links.demo, '_blank', 'noopener,noreferrer');
                      }}
                      role="link"
                      tabIndex={0}
                      aria-label={`${project.title} live demo`}
                    >
                      <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
                      Live
                    </span>
                  )}
                </div>
              )}
            </div>
          </Link>
        </li>
      ))}
    </ul>
  );
};

export default Projects;
