import { certificates } from '../data/certificates';

const Certificates = () => {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
      {certificates.map((cert) => (
        <a
          key={cert.title}
          href={cert.image}
          target="_blank"
          rel="noopener noreferrer"
          className="block rounded-xl bg-elevated overflow-hidden hover:opacity-90 transition-opacity"
        >
          <img
            src={cert.image}
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