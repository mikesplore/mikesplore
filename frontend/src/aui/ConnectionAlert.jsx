export default function ConnectionAlert({
  title = 'Lost connection',
  message = 'The voice session dropped. Check your connection and tap the mic to reconnect.',
}) {
  return (
    <section className="w-full max-w-sm rounded-2xl border border-red-500/60 bg-card px-5 py-4" role="alert">
      <div className="flex gap-3">
        <span className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-red-500" aria-hidden="true" />
        <div>
          <p className="text-sm font-semibold text-ink">{title}</p>
          <p className="mt-1 text-xs leading-relaxed text-muted">{message}</p>
        </div>
      </div>
    </section>
  );
}
