import Voice from './pages/Voice';
import { useEffect } from 'react';
import { fetchAssets } from './lib/voiceApi';
import './index.css';

function App() {
  useEffect(() => {
    if (window.location.pathname === '/talk' || window.location.pathname === '/talk/') {
      window.history.replaceState({}, '', '/');
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    fetchAssets(controller.signal).then((assets) => {
      const profileImage = assets.find((asset) => asset.asset_type === 'profile-image')?.url;
      if (!profileImage) return;
      document.querySelectorAll('link[rel="icon"], link[rel="apple-touch-icon"]').forEach((link) => { link.href = profileImage; });
    }).catch((error) => {
      if (error.name !== 'AbortError') console.warn('Profile icon unavailable', error);
    });
    return () => controller.abort();
  }, []);

  return <Voice />;
}

export default App;
