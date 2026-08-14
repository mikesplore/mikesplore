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
            I'm a software engineer based in Mombasa who builds backend systems, Android applications, and
            distributed AI-powered tools. My journey started in 2023 during my second year of computer science. I
            took the coursework seriously, but I quickly realized the real learning happens when you start building.
          </p>
          <p>
            Things kicked into gear during my attachment at SwahiliPot Hub. It opened my eyes to the local tech
            ecosystem, introduced me to Google's developer ecosystem, and pushed me out of my comfort zone with different
            stacks, architectural patterns, and the practical side of building systems with AI. That's where my
            engineering identity really formed.
          </p>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold text-ink">What I Build</h2>
          <p>
            I work primarily with Python and Kotlin, but my real focus is figuring out how systems fit together.
            Recently that's meant building{' '}
            <span className="font-medium text-ink">Vela</span>, a distributed AI assistant ecosystem connecting Linux
            hosts, Android clients, cloud infrastructure, and MCP-compatible AI agents.
          </p>
          <p>
            Vela isn't a single app. It's a system where multiple actors interact: an AI agent reaches a
            Linux machine through MCP, a mobile client talks to it over a cloud relay, and everything coordinates
            through WebSockets, SSE, and authenticated remote machine control. That means solving real engineering problems:
            reaching a host behind NAT, mapping MCP tools to actual capabilities, streaming long-running operations,
            managing credentials across a long-lived HTTP service, and keeping the architecture extensible as new
            clients and tools get added.
          </p>
          <p>
            Before Vela, that same instinct showed up in constraint-aware systems like university timetable
            generators, custom Django backends behind Nginx proxies, and offline-first Android applications with
            on-device automation logic. I prefer setting up my own production environments and understanding the full
            depth of the stack I'm shipping.
          </p>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold text-ink">How I Think About Engineering</h2>
          <p>
            I care about system boundaries, reliability, and shipping software that actually works in production. I
            enjoy the hard questions: how do multiple clients interact with one host, how do you authenticate remote
            operations, how do you keep a growing system extensible instead of tangled. That's the kind of work
            I want to keep doing.
          </p>
          <p>
            For a complete look at the systems I've built, start with{' '}
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

        <section className="space-y-3">
          <h2 className="text-xl font-semibold text-ink">What I'm Looking For</h2>
          <p>
            I'm looking for my next full-time role, somewhere I can work on real engineering problems alongside
            people who care about rigor, ownership, and building things that last.
          </p>
        </section>
      </div>
    </div>
  );
};

export default Home;