import { useEffect } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import Header from './Header';
import Nav from './Nav';

const Layout = () => {
  const { pathname } = useLocation();

  useEffect(() => {
    const pageNames = {
      '/timeline': 'Timeline',
      '/hackathons': 'Hackathons',
      '/certificates': 'Certificates',
      '/events': 'Events',
      '/bucket-list': 'Bucket List',
      '/cv': 'CV',
      '/contact': 'Contact',
      '/projects': 'Projects',
    };
    const projectMatch = pathname.match(/^\/projects\/([^/]+)$/);
    const pageName = projectMatch
      ? projectMatch[1].replace(/-/g, ' ')
      : pageNames[pathname];
    const canonicalUrl = `https://www.mikesplore.me${pathname === '/' ? '/' : pathname}`;

    document.title = pageName
      ? `${pageName.replace(/\b\w/g, (letter) => letter.toUpperCase())} | Michael Odhiambo`
      : 'Michael Odhiambo';

    let canonical = document.querySelector('link[rel="canonical"]');
    if (!canonical) {
      canonical = document.createElement('link');
      canonical.setAttribute('rel', 'canonical');
      document.head.appendChild(canonical);
    }
    canonical.setAttribute('href', canonicalUrl);
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
