export default function MediaDropzone({ onChoose, onDrop, accept = 'image/jpeg,image/png', title = 'Drop an image here, or tap to choose one', hint = 'JPG or PNG, up to 5MB' }) {
  function handleDrop(event) {
    event.preventDefault();
    onDrop?.(event.dataTransfer.files?.[0] || null);
  }

  return (
    <section className="w-full max-w-sm rounded-2xl border border-divider bg-card p-5 shadow-xl" aria-label="Choose an image">
      <label
        className="flex min-h-20 cursor-pointer flex-col items-center justify-center rounded-xl border border-dashed border-divider bg-elevated px-4 text-center transition hover:border-accent focus-within:ring-2 focus-within:ring-accent"
        onDragOver={(event) => event.preventDefault()}
        onDrop={handleDrop}
      >
        <span className="text-xs text-muted">{title}</span>
        <span className="mt-1 text-[11px] text-subtle">{hint}</span>
        <input type="file" accept={accept} className="sr-only" onChange={(event) => onChoose?.(event.target.files?.[0] || null)} />
      </label>
    </section>
  );
}
