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
import './index.css';

function App() {
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
