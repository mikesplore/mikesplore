export default function OwnerModeBadge({ active = true, onLock }) {
  return (
    <div className="flex items-center gap-2">
      <span className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-medium ${active ? 'border-teal/60 text-teal' : 'border-divider text-muted'}`}>
        <span className={`h-1.5 w-1.5 rounded-full ${active ? 'bg-teal' : 'bg-muted'}`} aria-hidden="true" />
        {active ? 'Owner mode' : 'Read-only'}
      </span>
      {active && <button type="button" onClick={onLock} aria-label="Lock owner mode" className="rounded-xl border border-divider bg-card px-2.5 py-1.5 text-xs text-muted transition hover:text-ink focus:outline-none focus:ring-2 focus:ring-accent">Lock</button>}
    </div>
  );
}
