import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import Home from './pages/Home';
import Timeline from './pages/Timeline';
import Projects from './pages/Projects';
import ProjectDetail from './pages/ProjectDetail';
import Hackathons from './pages/Hackathons';
import Certificates from './pages/Certificates';
import Events from './pages/Events';
import Contact from './pages/Contact';
import Cv from './pages/Cv';
import BucketList from './pages/BucketList';
import { useEffect } from 'react';
import { fetchAssets } from './lib/portfolioApi';
import './index.css';

function App() {
  useEffect(() => {
    const controller = new AbortController();
    fetchAssets(controller.signal).then((assets) => {
      const profileImage = assets.find((asset) => asset.asset_type === 'profile-image')?.url;
      if (!profileImage) return;
      document.querySelectorAll('link[rel="icon"], link[rel="apple-touch-icon"]').forEach((link) => {
        link.href = profileImage;
      });
    }).catch((error) => {
      if (error.name !== 'AbortError') console.warn('Profile icon unavailable', error);
    });
    return () => controller.abort();
  }, []);

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Home />} />
          <Route path="projects" element={<Projects />} />
          <Route path="projects/:projectId" element={<ProjectDetail />} />
          <Route path="timeline" element={<Timeline />} />
          <Route path="hackathons" element={<Hackathons />} />
          <Route path="certificates" element={<Certificates />} />
          <Route path="events" element={<Events />} />
          <Route path="bucket-list" element={<BucketList />} />
          <Route path="cv" element={<Cv />} />
          <Route path="about" element={<Navigate to="/" replace />} />
          <Route path="contact" element={<Contact />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
