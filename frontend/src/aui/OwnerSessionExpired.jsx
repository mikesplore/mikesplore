export default function OwnerSessionExpired({
  message = 'Owner session expired after 5 minutes of inactivity',
  hint = 'Say an owner command to unlock again',
}) {
  return (
    <section className="w-full max-w-sm rounded-2xl border border-divider bg-card px-5 py-5 text-center" role="status">
      <p className="text-sm text-muted">{message}</p>
      <p className="mt-1 text-xs text-subtle">{hint}</p>
    </section>
  );
}
