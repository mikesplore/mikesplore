/**
 * Compact confirmation card for replacing an existing media item.
 *
 * This is intentionally presentation-only. Uploading and replacement remain
 * the responsibility of the parent flow.
 */
import { formatFileSize } from './formatFileSize';

export default function MediaReplaceCard({
  fileName = 'profile-photo.jpg',
  fileSize,
  fileSizeBytes,
  status = 'Ready to publish',
  previewUrl = '',
  onCancel,
  onReplace,
  actionLabel = 'Replace photo',
}) {
  return (
    <section className="w-full max-w-sm rounded-2xl border border-divider bg-card p-5 shadow-xl" aria-label="Replace media">
      <div className="flex items-center gap-3">
        <div className="h-12 w-12 shrink-0 overflow-hidden rounded-xl bg-elevated" aria-hidden="true">
          {previewUrl && <img src={previewUrl} alt="" className="h-full w-full object-cover" />}
        </div>
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-ink">{fileName}</p>
          <p className="mt-0.5 truncate text-xs text-muted">{fileSize || formatFileSize(fileSizeBytes)} · {status}</p>
        </div>
      </div>

      <div className="mt-4 grid grid-cols-2 gap-2">
        <button
          type="button"
          onClick={onCancel}
          className="h-10 rounded-xl border border-divider bg-elevated px-3 text-sm font-semibold text-ink transition hover:bg-[var(--color-hover)] focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-2 focus:ring-offset-card"
        >
          Cancel
        </button>
        <button
          type="button"
          onClick={onReplace}
          className="h-10 rounded-xl bg-accent px-3 text-sm font-semibold text-on-accent transition hover:brightness-95 focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-2 focus:ring-offset-card"
        >
          {actionLabel}
        </button>
      </div>
    </section>
  );
}
