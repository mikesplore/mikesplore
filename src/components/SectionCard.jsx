const SectionCard = ({ title, description, icon: Icon, children, className = '' }) => {
  return (
    <section className={`rounded-2xl bg-card p-5 sm:p-6 ${className}`}>
      <div className="flex items-start gap-3 pb-5">
        {Icon && (
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-accent-soft text-accent">
            <Icon className="h-5 w-5" aria-hidden="true" />
          </div>
        )}
        <div>
          <h2 className="text-lg font-semibold text-ink">{title}</h2>
          {description && <p className="mt-1 text-base text-muted">{description}</p>}
        </div>
      </div>
      <hr className="divider" />
      <div className="pt-5">{children}</div>
    </section>
  );
};

export default SectionCard;
