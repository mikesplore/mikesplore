import { useState } from 'react';

export default function ProfileEditForm({ initialProfile = {}, onSave, onCancel }) {
  const [values, setValues] = useState({
    name: '', tagline: '', location: '', focus: '', experience: '', availability_status: '', availability_detail: '', about: '',
    ...initialProfile,
  });
  const [saving, setSaving] = useState(false);
  const [confirming, setConfirming] = useState(false);

  async function submit(event) {
    event.preventDefault();
    if (!values.name.trim() || saving) return;
    if (!confirming) { setConfirming(true); return; }
    setSaving(true);
    await onSave(Object.fromEntries(Object.entries(values).map(([key, value]) => [key, value.trim()])));
    setSaving(false);
  }

  return <form onSubmit={submit} className="mx-auto w-full max-w-sm rounded-2xl border border-divider bg-card p-5 text-left shadow-xl">
    <p className="text-sm font-semibold text-ink">Update profile</p>
    <div className="mt-4 max-h-[48vh] space-y-3 overflow-y-auto pr-1">
      {[['name', 'Name'], ['tagline', 'Tagline'], ['location', 'Location'], ['focus', 'Focus'], ['experience', 'Experience'], ['availability_status', 'Availability status'], ['availability_detail', 'Availability detail'], ['about', 'About']].map(([key, label]) => <label key={key} className="block text-xs font-medium text-muted" htmlFor={`profile-${key}`}>
        {label}
        {key === 'experience' || key === 'availability_detail' || key === 'about' ? <textarea id={`profile-${key}`} value={values[key]} onChange={(event) => setValues((current) => ({ ...current, [key]: event.target.value }))} rows={key === 'about' ? 4 : 2} className="mt-1 w-full resize-y rounded-xl border border-divider bg-elevated px-3 py-2 text-sm text-ink outline-none focus:border-accent" /> : <input id={`profile-${key}`} value={values[key]} onChange={(event) => setValues((current) => ({ ...current, [key]: event.target.value }))} className="mt-1 h-10 w-full rounded-xl border border-divider bg-elevated px-3 text-sm text-ink outline-none focus:border-accent" />}
      </label>)}
    </div>
    <div className="mt-4 grid grid-cols-2 gap-2">
      <button type="button" onClick={() => confirming ? setConfirming(false) : onCancel()} className="h-10 rounded-xl border border-divider bg-elevated text-sm font-semibold text-ink">{confirming ? 'Back' : 'Cancel'}</button>
      <button type="submit" disabled={saving || !values.name.trim()} className="h-10 rounded-xl bg-accent text-sm font-semibold text-on-accent disabled:opacity-50">{saving ? 'Saving…' : confirming ? 'Confirm save' : 'Review changes'}</button>
    </div>
  </form>;
}
