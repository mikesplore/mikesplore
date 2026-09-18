export default function VoiceOrb({ active = false, mode = 'idle', intensity = 0, label = 'Listening', showLabel = true }) {
  const motion = mode === 'speaking'
    ? 'animate-[pulse_0.8s_ease-in-out_infinite]'
    : '';
  const rippleMotion = active ? 'animate-[voice-ripple_1.8s_ease-out_infinite]' : '';
  const level = Math.max(0, Math.min(1, intensity));

  return (
    <div className="flex flex-col items-center gap-4" aria-label={label}>
      <div className={`relative flex h-52 w-52 items-center justify-center ${motion}`}>
        {[0, 1, 2, 3].map((ring) => <div key={ring} className={`absolute inset-8 rounded-full border-2 border-accent/60 ${rippleMotion}`} style={{ animationDelay: `${ring * 450}ms`, opacity: active ? 0.45 + level * 0.55 : 0.25, animationDuration: `${Math.max(0.9, 1.8 - level * 0.7)}s` }} aria-hidden="true" />)}
        <div className="relative h-24 w-24 rounded-full bg-accent shadow-[0_0_28px_rgba(245,158,11,0.28)] transition-transform duration-100" style={{ transform: `scale(${1 + level * 0.18})` }} aria-hidden="true" />
      </div>
      {showLabel && <span className="font-serif text-lg italic text-muted">{label}…</span>}
    </div>
  );
}
