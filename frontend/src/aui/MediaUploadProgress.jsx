import { formatFileSize } from './formatFileSize';

export default function MediaUploadProgress({
  fileName = 'profile-photo.jpg',
  fileSize,
  fileSizeBytes,
  progress = 55,
}) {
  const safeProgress = Math.max(0, Math.min(100, progress));

  return (
    <section className="w-full max-w-sm rounded-2xl border border-divider bg-card p-5 shadow-xl" aria-live="polite" aria-label="Uploading media">
      <div className="flex items-center gap-3">
        <div className="h-12 w-12 shrink-0 rounded-xl bg-elevated" aria-hidden="true" />
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-ink">{fileName}</p>
          <p className="mt-0.5 truncate text-xs text-muted">{fileSize || formatFileSize(fileSizeBytes)} · Uploading…</p>
        </div>
      </div>
      <div className="mt-4 h-1 overflow-hidden rounded-full bg-elevated" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow={safeProgress}>
        <div className="h-full rounded-full bg-accent transition-[width] duration-300" style={{ width: `${safeProgress}%` }} />
      </div>
    </section>
  );
}
