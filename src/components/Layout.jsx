import { Outlet } from 'react-router-dom';
import Header from './Header';
import Nav from './Nav';

const Layout = () => {
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
