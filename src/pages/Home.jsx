import { Link } from 'react-router-dom';
import AvailabilityBanner from '../components/AvailabilityBanner';

const Home = () => {
  return (
    <div className="space-y-8">
      <AvailabilityBanner />

      <div className="space-y-8 text-base leading-relaxed text-muted">
        <section className="space-y-3">
          <h2 className="text-xl font-semibold text-ink">The Backstory</h2>
          <p>
            I&apos;m a software engineer based in Mombasa, specializing in full-stack, backend, and Android
            development. My journey started back in 2023 during my second year of computer science. I took the
            coursework seriously  but I quickly realized
            the real learning happens when you start building.
          </p>
          <p>
            Things really kicked into gear during my attachment at SwahiliPot Hub. It opened my eyes to the local
            tech ecosystem and community events. It&apos;s where I made my first solid tech friends out of school,
            got exposed to Google ecosystems, and learned how to practically build systems using AI. It also pushed
            me out of my comfort zone, exposing me to different stacks and architectural patterns beyond my usual
            go-tos.
          </p>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold text-ink">What I Build</h2>
          <p>
            Most days, you&apos;ll find me writing Python or Kotlin. I enjoy solving tricky runtime and architectural
            problems. Whether that&apos;s building constraint-aware systems like university timetable generators,
            deploying custom Django backends behind Nginx proxies, or designing offline-first Android applications
            with on-device automation logic, I focus on making things fast, stable, and practical.
          </p>
          <p>
            I prefer setting up my own production environments, managing my own server configurations, and actually
            understanding the full depth of the stack I&apos;m shipping.
          </p>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold text-ink">Beyond the Code</h2>
          <p>
            When I&apos;m not staring at a terminal or debugging database logs, I&apos;m usually gaming or
            traveling to clear my head. I think keeping a balance outside of engineering is what keeps the building
            part fun.
          </p>
          <p>
            Right now, I&apos;m looking for my next full-time role. I&apos;m looking to join a fast-moving team that
            values engineering rigor and cares about shipping software that actually works in production.
          </p>
          <p>
            For a complete look at the systems I&apos;ve built, start with{' '}
            <Link to="/projects" className="font-medium text-accent hover:text-accent/80">
              projects
            </Link>{' '}
            and then browse the{' '}
            <Link to="/timeline" className="font-medium text-accent hover:text-accent/80">
              timeline
            </Link>
            .
          </p>
        </section>
      </div>
    </div>
  );
};

export default Home;
