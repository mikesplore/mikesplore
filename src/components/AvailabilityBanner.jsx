import { Link } from 'react-router-dom';
import { Briefcase } from 'lucide-react';
import { availability } from '../data/profile';

const AvailabilityBanner = () => {
  return (
    <div className="rounded-2xl bg-accent-soft p-5 sm:p-6">
      <div className="flex items-start gap-3">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-accent/15 text-accent">
          <Briefcase className="h-5 w-5" aria-hidden="true" />
        </div>
        <div>
          <p className="text-base font-semibold text-ink">{availability.status}</p>
          <p className="mt-1 text-base leading-relaxed text-muted">{availability.detail}</p>
          <Link
            to="/contact"
            className="mt-3 inline-flex text-base font-medium text-accent hover:text-accent/80"
          >
            Get in touch →
          </Link>
        </div>
      </div>
    </div>
  );
};

export default AvailabilityBanner;
