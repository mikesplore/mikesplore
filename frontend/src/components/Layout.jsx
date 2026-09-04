import { useEffect } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import Header from './Header';
import Nav from './Nav';
import { fetchProfile } from '../lib/portfolioApi';

const Layout = () => {
  const { pathname } = useLocation();

  useEffect(() => {
    const controller = new AbortController();
    fetchProfile(controller.signal).then((profile) => {
      const owner = profile.name || 'Portfolio';
      const pageNames = { '/': 'Home', '/timeline': 'Timeline', '/projects': 'Projects', '/hackathons': 'Hackathons', '/certificates': 'Certificates', '/events': 'Events', '/bucket-list': 'Bucket List', '/cv': 'CV', '/contact': 'Contact' };
      const projectMatch = pathname.match(/^\/projects\/([^/]+)$/);
      const pageName = projectMatch?.[1].replace(/-/g, ' ').replace(/\b\w/g, (letter) => letter.toUpperCase()) || pageNames[pathname] || 'Portfolio';
      const pageTitle = pathname === '/' ? owner : `${pageName} | ${owner}`;
      const pageDescription = profile.tagline || `${pageName} from ${owner}'s portfolio.`;
      const canonicalUrl = `${window.location.origin}${pathname === '/' ? '/' : pathname}`;

    document.title = pageTitle;

    let canonical = document.querySelector('link[rel="canonical"]');
    if (!canonical) {
      canonical = document.createElement('link');
      canonical.setAttribute('rel', 'canonical');
      document.head.appendChild(canonical);
    }
    canonical.setAttribute('href', canonicalUrl);

    let description = document.querySelector('meta[name="description"]');
    if (!description) {
      description = document.createElement('meta');
      description.setAttribute('name', 'description');
      document.head.appendChild(description);
    }
    description.setAttribute('content', pageDescription);

    let ogTitle = document.querySelector('meta[property="og:title"]');
    if (ogTitle) ogTitle.setAttribute('content', pageTitle);
    let ogDescription = document.querySelector('meta[property="og:description"]');
    if (ogDescription) ogDescription.setAttribute('content', pageDescription);
    let ogUrl = document.querySelector('meta[property="og:url"]');
    if (ogUrl) ogUrl.setAttribute('content', canonicalUrl);
    }).catch(() => undefined);
    return () => controller.abort();
  }, [pathname]);

  return (
    <div className="min-h-screen bg-page text-ink font-sans">
      <div className="mx-auto max-w-3xl px-5 sm:px-6 py-6 sm:py-8">
        <Header />
        <Nav />
        <main className="pt-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
};

export default Layout;
