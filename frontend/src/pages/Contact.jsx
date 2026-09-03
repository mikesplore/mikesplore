import { Briefcase, ExternalLink, Mail, MessageCircle, Users } from 'lucide-react';
import { socialLinks, availability, contactSocials, username } from '../data/profile';
import SectionCard from '../components/SectionCard';
import SocialIcon from '../components/SocialIcon';

const LinkCard = ({ name, href, subtitle }) => (
  <a
    href={href}
    target="_blank"
    rel="noopener noreferrer"
    className="flex items-center gap-3 rounded-xl bg-elevated px-4 py-4 transition-colors hover:bg-[var(--color-hover)]"
  >
    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-accent-soft text-accent">
      <SocialIcon name={name} className="h-5 w-5" />
    </div>
    <div className="min-w-0 flex-1">
      <div className="text-base font-medium text-ink">{name}</div>
      <div className="truncate text-sm text-subtle">{subtitle}</div>
    </div>
    <ExternalLink className="h-4 w-4 shrink-0 text-subtle" aria-hidden="true" />
  </a>
);

const Contact = () => {
  const emailLink = socialLinks.find((link) => link.name === 'Email')?.url || 'mailto:mikepremium8@gmail.com';
  const professionalLinks = socialLinks.filter((link) => link.name !== 'Email');
  const messagingLinks = contactSocials.filter((social) => ['WhatsApp', 'Telegram'].includes(social.name));
  const socialLinksList = contactSocials.filter((social) => !['WhatsApp', 'Telegram'].includes(social.name));

  return (
    <div className="space-y-6">
      <div className="rounded-2xl bg-accent-soft p-5 sm:p-6">
        <div className="flex items-start gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-accent/15 text-accent">
            <Briefcase className="h-5 w-5" aria-hidden="true" />
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-base font-semibold text-ink">{availability.status}</p>
            <p className="mt-1 text-base leading-relaxed text-muted">{availability.detail}</p>
            <a
              href={emailLink}
              className="mt-4 inline-flex items-center gap-2 rounded-xl bg-accent px-5 py-2.5 text-base font-medium text-on-accent transition-opacity hover:opacity-90"
            >
              <Mail className="h-4 w-4" />
              Email me
            </a>
          </div>
        </div>
      </div>

      <SectionCard
        title="Professional"
        description="Code, writing, and community profiles."
        icon={Briefcase}
      >
        <div className="grid gap-3 sm:grid-cols-2">
          {professionalLinks.map((link) => (
            <LinkCard
              key={link.name}
              name={link.name}
              href={link.url}
              subtitle={link.label}
            />
          ))}
        </div>
      </SectionCard>

      <SectionCard
        title="Messaging"
        description="Fastest way to reach me."
        icon={MessageCircle}
      >
        <div className="grid gap-3 sm:grid-cols-2">
          {messagingLinks.map((social) => (
            <LinkCard
              key={social.name}
              name={social.name}
              href={social.url}
              subtitle={`@${social.handle}`}
            />
          ))}
        </div>
      </SectionCard>

      <SectionCard
        title="Social"
        description={`@${username} on most platforms.`}
        icon={Users}
      >
        <div className="grid gap-3 sm:grid-cols-2">
          {socialLinksList.map((social) => (
            <LinkCard
              key={social.name}
              name={social.name}
              href={social.url}
              subtitle={`@${social.handle}`}
            />
          ))}
        </div>
      </SectionCard>
    </div>
  );
};

export default Contact;
