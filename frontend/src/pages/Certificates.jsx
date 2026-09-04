import { useEffect, useState } from 'react';
import { fetchCertificates } from '../lib/portfolioApi';
import EmptyState from '../components/EmptyState';

const Certificates = () => {
  const [certificates, setCertificates] = useState([]);
  const [status, setStatus] = useState('loading');
  useEffect(() => {
    const controller = new AbortController();
    fetchCertificates(controller.signal).then((items) => { setCertificates(items); setStatus('ready'); }).catch((error) => { if (error.name !== 'AbortError') setStatus('error'); });
    return () => controller.abort();
  }, []);
  if (status === 'loading') return <p className="py-8 text-center text-base text-subtle">Loading certificates…</p>;
  if (status === 'error') return <p className="py-8 text-center text-base text-subtle">Certificates are temporarily unavailable.</p>;
  if (certificates.length === 0) return <EmptyState title="No certificates to show yet">Certificates will appear here once they are uploaded.</EmptyState>;
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
      {certificates.map((cert) => (
        <a
          key={cert.title}
          href={cert.image_url}
          target="_blank"
          rel="noopener noreferrer"
          className="block rounded-xl bg-elevated overflow-hidden hover:opacity-90 transition-opacity"
        >
          <img
            src={cert.image_url}
            alt={cert.title}
            className="w-full h-48 sm:h-56 object-cover"
            loading="lazy"
          />
          <div className="p-3">
            <h2 className="text-base font-medium text-ink">{cert.title}</h2>
          </div>
        </a>
      ))}
    </div>
  );
};

export default Certificates;
