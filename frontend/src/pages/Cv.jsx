import { ExternalLink, GraduationCap, BriefcaseBusiness } from 'lucide-react';
import { useEffect, useState } from 'react';
import SectionCard from '../components/SectionCard';
import { fetchAssets, fetchEducation, fetchWorkExperience } from '../lib/portfolioApi';
import EmptyState from '../components/EmptyState';

const Cv = () => {
  const [education, setEducation] = useState([]);
  const [workExperience, setWorkExperience] = useState([]);
  const [status, setStatus] = useState('loading');
  const [cvUrl, setCvUrl] = useState('');
  useEffect(() => {
    const controller = new AbortController();
    Promise.all([fetchEducation(controller.signal), fetchWorkExperience(controller.signal), fetchAssets(controller.signal)]).then(([items, experience, assets]) => { setEducation(items); setWorkExperience(experience); setCvUrl(assets.find((asset) => asset.asset_type === 'cv')?.url || ''); setStatus('ready'); }).catch((error) => { if (error.name !== 'AbortError') setStatus('error'); });
    return () => controller.abort();
  }, []);
  if (status === 'loading') return <p className="py-8 text-center text-base text-subtle">Loading CV details…</p>;
  if (status === 'error') return <p className="py-8 text-center text-base text-subtle">CV details are temporarily unavailable.</p>;
  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-base text-muted">Here's my CV</p>
        <a
          href={cvUrl || undefined}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1.5 text-sm font-medium text-accent hover:text-accent/80"
        >
          {cvUrl ? 'Open in new tab' : 'CV not available yet'}
          <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
        </a>
      </div>

      {cvUrl ? <div className="overflow-hidden rounded-xl border border-divider bg-elevated">
        <iframe src={cvUrl} title="Portfolio owner CV" className="h-[min(80vh,900px)] w-full" />
      </div> : <EmptyState title="CV not available yet">The CV will appear here once it has been uploaded.</EmptyState>}

      <SectionCard title="Work Experience" icon={BriefcaseBusiness}>
        {workExperience.length === 0 ? <EmptyState title="No work experience details yet">Work history will appear here once it is added.</EmptyState> : <ul className="space-y-4">
          {workExperience.map((item) => (
            <li key={item.id} className="rounded-xl bg-elevated px-4 py-4">
              <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
                <div className="text-base font-medium text-ink">{item.role}</div>
                {item.period && <div className="text-sm text-subtle">{item.period}</div>}
              </div>
              <div className="mt-1 text-base text-muted">{item.organization}{item.location ? ` · ${item.location}` : ''}{item.employment_type ? ` · ${item.employment_type}` : ''}</div>
              {item.description && <p className="mt-2 text-sm text-muted">{item.description}</p>}
              {item.highlights?.length > 0 && <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-muted">{item.highlights.map((point, index) => <li key={`${item.id}-${index}`}>{point}</li>)}</ul>}
            </li>
          ))}
        </ul>}
      </SectionCard>

      <SectionCard title="Education" icon={GraduationCap}>
        {education.length === 0 ? <EmptyState title="No education details yet">Education history will appear here once it is added.</EmptyState> : <ul className="space-y-4">
          {education.map((item) => (
            <li key={item.school} className="rounded-xl bg-elevated px-4 py-4">
              <div className="text-base font-medium text-ink">{item.degree}</div>
              <div className="mt-1 text-base text-muted">{item.school}</div>
              <div className="mt-1 text-sm text-subtle">
                {item.location} · {item.period}
              </div>
            </li>
          ))}
        </ul>}
      </SectionCard>
    </div>
  );
};

export default Cv;
