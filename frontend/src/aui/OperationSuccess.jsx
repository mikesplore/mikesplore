export default function OperationSuccess({
  title = 'Profile photo updated',
  message = 'Live on mikesplore.me now',
}) {
  return (
    <section className="flex w-full max-w-sm items-center gap-3 rounded-2xl border border-divider bg-card px-5 py-4 shadow-xl" role="status">
      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-teal/20 text-lg text-teal" aria-hidden="true">✓</span>
      <div className="min-w-0">
        <p className="truncate text-sm font-semibold text-ink">{title}</p>
        <p className="mt-0.5 truncate text-xs text-muted">{message}</p>
      </div>
    </section>
  );
}
