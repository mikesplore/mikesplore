import { useEffect } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import Header from './Header';
import Nav from './Nav';

const Layout = () => {
  const { pathname } = useLocation();

  useEffect(() => {
    const pageMetadata = {
      '/': {
        title: 'Michael Odhiambo',
        description: 'Michael Odhiambo - full-stack developer building Kotlin backends, Android apps, and LLM-assisted tooling.',
      },
      '/timeline': { title: 'Timeline', description: 'Michael Odhiambo\'s development, writing, and career timeline.' },
      '/projects': { title: 'Projects', description: 'Selected software projects by Michael Odhiambo.' },
      '/hackathons': { title: 'Hackathons', description: 'Hackathons and competitions completed by Michael Odhiambo.' },
      '/certificates': { title: 'Certificates', description: 'Professional certificates and learning achievements earned by Michael Odhiambo.' },
      '/events': { title: 'Events', description: 'Events and community activities involving Michael Odhiambo.' },
      '/bucket-list': { title: 'Bucket List', description: 'Michael Odhiambo\'s goals, ambitions, and things to experience.' },
      '/cv': { title: 'CV', description: 'Michael Odhiambo\'s curriculum vitae and professional experience.' },
      '/contact': { title: 'Contact', description: 'Get in touch with Michael Odhiambo.' },
    };
    const projectMatch = pathname.match(/^\/projects\/([^/]+)$/);
    const projectName = projectMatch?.[1].replace(/-/g, ' ');
    const metadata = projectName
      ? { title: projectName.replace(/\b\w/g, (letter) => letter.toUpperCase()), description: `A software project by Michael Odhiambo: ${projectName}.` }
      : pageMetadata[pathname] || pageMetadata['/'];
    const pageTitle = metadata.title === 'Michael Odhiambo'
      ? metadata.title
      : `${metadata.title} | Michael Odhiambo`;
    const canonicalUrl = `https://www.mikesplore.me${pathname === '/' ? '/' : pathname}`;

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
    description.setAttribute('content', metadata.description);

    let ogTitle = document.querySelector('meta[property="og:title"]');
    if (ogTitle) ogTitle.setAttribute('content', pageTitle);
    let ogDescription = document.querySelector('meta[property="og:description"]');
    if (ogDescription) ogDescription.setAttribute('content', metadata.description);
    let ogUrl = document.querySelector('meta[property="og:url"]');
    if (ogUrl) ogUrl.setAttribute('content', canonicalUrl);
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
