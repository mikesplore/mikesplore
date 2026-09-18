const keys = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '', '0', 'backspace'];

export default function PinPad({
  title = 'Enter your PIN to update the profile picture',
  value = '',
  length = 4,
  attemptsLeft,
  error = '',
  onChange,
  onCancel,
}) {
  function press(key) {
    if (key === 'backspace') return onChange?.(value.slice(0, -1));
    if (!key || value.length >= length) return;
    onChange?.(`${value}${key}`);
  }

  return (
    <section className="w-full max-w-sm rounded-2xl border border-divider bg-card px-5 py-6 text-center shadow-xl" aria-label="Owner PIN">
      <p className="text-sm text-muted">{title}</p>
      {attemptsLeft !== undefined && <p className={`mt-4 text-xs ${error ? 'text-red-500' : 'text-muted'}`}>
        {error || `${attemptsLeft} attempt${attemptsLeft === 1 ? '' : 's'} left`}
      </p>}
      <div className="mt-3 flex justify-center gap-3" aria-label={`${value.length} of ${length} PIN digits entered`}>
        {Array.from({ length }, (_, index) => <span key={index} className={`h-3 w-3 rounded-full border ${index < value.length ? 'border-accent bg-accent' : 'border-muted'}`} />)}
      </div>
      <div className="mx-auto mt-4 grid max-w-[220px] grid-cols-3 gap-2">
        {keys.map((key, index) => key ? <button key={key} type="button" onClick={() => press(key)} aria-label={key === 'backspace' ? 'Delete last digit' : `Enter ${key}`} className="h-14 rounded-xl border border-divider bg-elevated text-base font-semibold text-ink transition hover:bg-[var(--color-hover)] focus:outline-none focus:ring-2 focus:ring-accent">
          {key === 'backspace' ? '⌫' : key}
        </button> : <span key={`empty-${index}`} aria-hidden="true" />)}
      </div>
      <button type="button" onClick={onCancel} className="mt-4 text-xs font-medium text-muted hover:text-ink">Cancel</button>
    </section>
  );
}
