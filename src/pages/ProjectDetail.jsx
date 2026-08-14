import { useParams, Link } from 'react-router-dom';
import { ExternalLink, Github, ArrowLeft } from 'lucide-react';
import { projectsCatalog } from '../data/projectsCatalog';
import SectionCard from '../components/SectionCard';

const ProjectDetail = () => {
  const { projectId } = useParams();
  const project = projectsCatalog.find((p) => p.id === projectId);

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

  const hasGallery = project.gallery && project.gallery.length > 0;
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
      <SectionCard>
        <div className="space-y-4">
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

          {/* Gallery */}
          {hasGallery && (
            <div>
              <h2 className="text-sm font-semibold text-ink uppercase tracking-wide mb-3">
                Gallery
              </h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {project.gallery.map((img, idx) => (
                  <a
                    key={idx}
                    href={img}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="block rounded-lg overflow-hidden bg-elevated hover:opacity-90 transition-opacity"
                  >
                    <img
                      src={img}
                      alt={`${project.title} screenshot ${idx + 1}`}
                      className="w-full h-48 object-cover"
                      loading="lazy"
                    />
                  </a>
                ))}
              </div>
            </div>
          )}

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
      </SectionCard>
    </div>
  );
};

export default ProjectDetail;
