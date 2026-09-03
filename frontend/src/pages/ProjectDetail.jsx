import { useParams, Link } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { ExternalLink, Github, ArrowLeft } from 'lucide-react';
import { fetchProjects } from '../lib/portfolioApi';
import SectionCard from '../components/SectionCard';

const ProjectDetail = () => {
  const { projectId } = useParams();
  const [project, setProject] = useState(null);
  const [status, setStatus] = useState('loading');
  useEffect(() => {
    const controller = new AbortController();
    fetchProjects(controller.signal).then((items) => {
      const item = items.find((entry) => entry.slug === projectId);
      setProject(item && { id: item.slug, title: item.title, summary: item.blurb, ...(item.details || {}), stack: item.tech_stack, tags: item.tags, links: item.links, ...(item.media || {}) });
      setStatus('ready');
    }).catch((error) => { if (error.name !== 'AbortError') setStatus('error'); });
    return () => controller.abort();
  }, [projectId]);
  if (status === 'loading') return <p className="py-8 text-center text-base text-subtle">Loading project…</p>;
  if (status === 'error') return <SectionCard title="Project unavailable"><p className="text-muted">Please try again later.</p></SectionCard>;

  if (!project) {
    return (
      <SectionCard title="Project Not Found">
        <div className="text-center py-8">
          <p className="text-muted mb-4">
            The project you're looking for doesn't exist or hasn't been added yet.
          </p>
          <Link
            to="/projects"
            className="inline-flex items-center gap-2 text-accent hover:text-accent/80 font-medium"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Projects
          </Link>
        </div>
      </SectionCard>
    );
  }

  const hasDetails = project.details;
  const hasRepo = project.links?.repo;
  const hasDemo = project.links?.demo;

  return (
    <div className="space-y-6">
      {/* Back link */}
      <Link
        to="/projects"
        className="inline-flex items-center gap-2 text-subtle hover:text-muted transition-colors"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to Projects
      </Link>

      {/* Main content */}
      <section className="rounded-2xl bg-card p-5 sm:p-6">
        <div className="space-y-4">
          {/* Hero cover image */}
          <div className="relative -mx-4 -mt-4 sm:-mx-5 sm:-mt-5 overflow-hidden rounded-t-xl">
            <img
              src={
                project.cardImage ||
                `https://ui-avatars.com/api/?name=${encodeURIComponent(project.title)}&size=512`
              }
              alt={`${project.title} cover`}
              className="h-48 sm:h-64 w-full object-cover"
              loading="lazy"
            />
            <div className="absolute inset-0 bg-gradient-to-t from-elevated via-elevated/40 to-transparent" />
          </div>

          {/* Header */}
          <div>
            <h1 className="text-2xl font-bold text-ink">{project.title}</h1>
            <p className="text-lg text-muted mt-1">{project.tagline}</p>
            
            {/* Tags */}
            {project.tags && project.tags.length > 0 && (
              <div className="flex flex-wrap gap-2 mt-3">
                {project.tags.map((tag) => (
                  <span
                    key={tag}
                    className="px-2.5 py-1 rounded-full text-xs font-medium bg-accent-soft text-accent"
                  >
                    {tag}
                  </span>
                ))}
              </div>
            )}
          </div>

          {/* Overview */}
          <div>
            <h2 className="text-sm font-semibold text-ink uppercase tracking-wide mb-2">
              Overview
            </h2>
            <p className="text-muted leading-relaxed">{project.overview}</p>
          </div>

          {/* Stack */}
          {project.stack && project.stack.length > 0 && (
            <div>
              <h2 className="text-sm font-semibold text-ink uppercase tracking-wide mb-2">
                Tech Stack
              </h2>
              <div className="flex flex-wrap gap-2">
                {project.stack.map((tech) => (
                  <span
                    key={tech}
                    className="px-2.5 py-1 rounded-md text-xs font-medium bg-elevated text-muted border border-divider"
                  >
                    {tech}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Details (optional) */}
          {hasDetails && (
            <div>
              <h2 className="text-sm font-semibold text-ink uppercase tracking-wide mb-2">
                Technical Details
              </h2>
              <p className="text-muted leading-relaxed">{project.details}</p>
            </div>
          )}

          {/* Links */}
          {(hasRepo || hasDemo) && (
            <div>
              <h2 className="text-sm font-semibold text-ink uppercase tracking-wide mb-2">
                Links
              </h2>
              <div className="flex flex-wrap gap-4">
                {hasRepo && (
                  <a
                    href={project.links.repo}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-2 text-teal hover:text-teal/80 font-medium transition-colors"
                  >
                    <Github className="h-4 w-4" />
                    GitHub Repository
                  </a>
                )}
                {hasDemo && (
                  <a
                    href={project.links.demo}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-2 text-accent hover:text-accent/80 font-medium transition-colors"
                  >
                    <ExternalLink className="h-4 w-4" />
                    Live Demo
                  </a>
                )}
              </div>
            </div>
          )}

          {/* Metadata pills */}
          <div className="flex flex-wrap gap-2 pt-2">
            <span className="px-2.5 py-1 rounded-full text-xs font-medium bg-teal-soft text-teal capitalize">
              {project.platform}
            </span>
            <span className="px-2.5 py-1 rounded-full text-xs font-medium bg-accent-soft text-accent capitalize">
              {project.type.replace('-', ' ')}
            </span>
            <span className="px-2.5 py-1 rounded-full text-xs font-medium bg-elevated text-muted capitalize">
              {project.status.replace('-', ' ')}
            </span>
          </div>
        </div>
      </section>
    </div>
  );
};

export default ProjectDetail;
