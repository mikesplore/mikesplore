import { ExternalLink, GraduationCap } from 'lucide-react';
import { useEffect, useState } from 'react';
import cvPdf from '../data/cv/Michael Odhiambo CV.pdf';
import SectionCard from '../components/SectionCard';
import { fetchEducation } from '../lib/portfolioApi';

const Cv = () => {
  const [education, setEducation] = useState([]);
  const [status, setStatus] = useState('loading');
  useEffect(() => {
    const controller = new AbortController();
    fetchEducation(controller.signal).then((items) => { setEducation(items); setStatus('ready'); }).catch((error) => { if (error.name !== 'AbortError') setStatus('error'); });
    return () => controller.abort();
  }, []);
  if (status === 'loading') return <p className="py-8 text-center text-base text-subtle">Loading CV details…</p>;
  if (status === 'error') return <p className="py-8 text-center text-base text-subtle">CV details are temporarily unavailable.</p>;
  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-base text-muted">Here's my CV</p>
        <a
          href={cvPdf}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1.5 text-sm font-medium text-accent hover:text-accent/80"
        >
          Open in new tab
          <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
        </a>
      </div>

      <div className="overflow-hidden rounded-xl border border-divider bg-elevated">
        <iframe
          src={cvPdf}
          title="Michael Odhiambo CV"
          className="h-[min(80vh,900px)] w-full"
        />
      </div>

      <SectionCard title="Education" icon={GraduationCap}>
        <ul className="space-y-4">
          {education.map((item) => (
            <li key={item.school} className="rounded-xl bg-elevated px-4 py-4">
              <div className="text-base font-medium text-ink">{item.degree}</div>
              <div className="mt-1 text-base text-muted">{item.school}</div>
              <div className="mt-1 text-sm text-subtle">
                {item.location} · {item.period}
              </div>
            </li>
          ))}
        </ul>
      </SectionCard>
    </div>
  );
};

export default Cv;
