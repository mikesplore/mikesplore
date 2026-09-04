const EmptyState = ({ title, children }) => (
  <div className="rounded-xl border border-dashed border-divider bg-elevated px-6 py-10 text-center">
    <p className="text-base font-medium text-ink">{title}</p>
    <p className="mx-auto mt-1.5 max-w-md text-sm leading-relaxed text-subtle">{children}</p>
  </div>
);

export default EmptyState;
