import profileImage from '../data/profile.jpg';
import { socialLinks, status } from '../data/profile';
import SocialIcon from './SocialIcon';
import ThemeToggle from './ThemeToggle';

const Header = () => {
  const pillSocials = socialLinks.filter((link) => link.name !== 'Email');

  return (
    <header className="pt-4 pb-6">
      <div className="flex items-start justify-between gap-3 sm:gap-6">
        <div className="min-w-0 flex-1">
          <h1 className="text-[clamp(1.25rem,4.5vw+0.25rem,3rem)] font-semibold tracking-tight text-ink whitespace-nowrap">
            Michael Odhiambo
          </h1>
          <p className="mt-2 text-sm text-muted sm:text-base">{status.tagline}</p>

          <ul className="mt-3 space-y-1.5 sm:mt-4 sm:space-y-2">
            <li className="flex items-center gap-2 text-sm text-muted sm:text-base">
              <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-accent" aria-hidden="true" />
              {status.experience}
            </li>
            <li className="flex items-center gap-2 text-sm text-muted sm:text-base">
              <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-accent" aria-hidden="true" />
              {status.location}
            </li>
            <li className="flex items-center gap-2 text-sm text-muted sm:text-base">
              <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-accent" aria-hidden="true" />
              {status.focus}
            </li>
          </ul>
        </div>

        <div className="flex shrink-0 flex-col items-end gap-3">
          <ThemeToggle />
          <div className="h-24 w-24 sm:h-32 sm:w-32 overflow-hidden rounded-2xl border border-divider bg-elevated">
            <img src={profileImage} alt="Michael Odhiambo" className="h-full w-full object-cover" />
          </div>
        </div>
      </div>

      <div className="scroll-pills -mx-5 mt-5 flex w-full gap-2 overflow-x-auto px-5 sm:-mx-6 sm:px-6">
        {pillSocials.map((link) => (
          <a
            key={link.name}
            href={link.url}
            target={link.url.startsWith('http') ? '_blank' : undefined}
            rel={link.url.startsWith('http') ? 'noopener noreferrer' : undefined}
            className="inline-flex shrink-0 items-center gap-1.5 rounded-full bg-elevated px-3.5 py-2 text-sm text-muted transition-colors hover:bg-[var(--color-hover)] hover:text-ink"
          >
            <SocialIcon name={link.name} />
            {link.label}
          </a>
        ))}
      </div>
    </header>
  );
};

export default Header;
