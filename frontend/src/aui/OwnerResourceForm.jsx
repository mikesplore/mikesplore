import { useEffect, useState } from 'react';

const fields = {
  project: [['title', 'Title'], ['slug', 'Slug'], ['blurb', 'Summary']],
  certificate: [['title', 'Title']],
  link: [['name', 'Name'], ['url', 'URL'], ['label', 'Label'], ['category', 'Category']],
  skill: [['category', 'Category'], ['items', 'Skills (comma-separated)']],
  education: [['degree', 'Degree'], ['school', 'School'], ['description', 'Description']],
  'bucket-list': [['title', 'Goal'], ['remark', 'Notes'], ['done', 'Completed (true/false)']],
};

export default function OwnerResourceForm({ resource, resourceKey = resource, token, apiBase, onSave, onCancel }) {
  const emptyValues = Object.fromEntries((fields[resource] || []).map(([key]) => [key, '']));
  const [values, setValues] = useState(emptyValues);
  const [records, setRecords] = useState([]);
  const [selectedId, setSelectedId] = useState('');
  const [operation, setOperation] = useState('create');
  const [confirming, setConfirming] = useState(false);
  const [file, setFile] = useState(null);
  const definition = fields[resource] || [];

  useEffect(() => {
    fetch(`${apiBase}/owner/resources/${resourceKey}`, { headers: { Authorization: `Bearer ${token}` } }).then((response) => response.ok ? response.json() : []).then(setRecords).catch(() => setRecords([]));
  }, [apiBase, resourceKey, token]);

  function selectRecord(id) {
    setSelectedId(id);
    const record = records.find((item) => String(item.id) === String(id));
    if (record) setValues(Object.fromEntries(definition.map(([key]) => [key, Array.isArray(record[key]) ? record[key].join(', ') : record[key] || ''])));
  }

  async function submit(event) {
    event.preventDefault();
    if (!confirming) { setConfirming(true); return; }
    const payload = Object.fromEntries(Object.entries(values).map(([key, value]) => [key, key === 'items' ? value.split(',').map((item) => item.trim()).filter(Boolean) : key === 'done' ? value.trim().toLowerCase() === 'true' : value.trim()]));
    if (file) payload.file = file;
    await onSave({ ...payload, action: operation, id: selectedId || undefined });
  }

  return <form onSubmit={submit} className="mx-auto w-full max-w-sm rounded-2xl border border-divider bg-card p-5 text-left shadow-xl">
    <p className="text-sm font-semibold capitalize text-ink">Manage {resource}</p>
    <div className="mt-4 grid grid-cols-3 gap-2">{['create', 'update', 'delete'].map((value) => <button key={value} type="button" onClick={() => { setOperation(value); setConfirming(false); }} className={`rounded-lg px-2 py-2 text-xs font-medium capitalize ${operation === value ? 'bg-accent text-on-accent' : 'bg-elevated text-muted'}`}>{value}</button>)}</div>
    {operation !== 'create' && <select value={selectedId} onChange={(event) => selectRecord(event.target.value)} className="mt-3 h-10 w-full rounded-xl border border-divider bg-elevated px-3 text-sm text-ink"><option value="">Choose existing {resource}</option>{records.map((record) => <option key={record.id} value={record.id}>{record.title || record.name || record.category || record.degree || record.id}</option>)}</select>}
    {operation !== 'delete' && <div className="mt-4 max-h-[48vh] space-y-3 overflow-y-auto pr-1">
      {definition.map(([key, label]) => <label key={key} className="block text-xs font-medium text-muted" htmlFor={`owner-${resource}-${key}`}>
        {label}
        {key === 'blurb' || key === 'description' ? <textarea id={`owner-${resource}-${key}`} rows="3" value={values[key]} onChange={(event) => setValues((current) => ({ ...current, [key]: event.target.value }))} className="mt-1 w-full rounded-xl border border-divider bg-elevated px-3 py-2 text-sm text-ink outline-none focus:border-accent" /> : <input id={`owner-${resource}-${key}`} value={values[key]} onChange={(event) => setValues((current) => ({ ...current, [key]: event.target.value }))} className="mt-1 h-10 w-full rounded-xl border border-divider bg-elevated px-3 text-sm text-ink outline-none focus:border-accent" />}
      </label>)}
      {resource === 'certificate' && <label className="block text-xs font-medium text-muted" htmlFor="owner-certificate-file">Certificate file<input id="owner-certificate-file" type="file" accept="image/*,application/pdf" onChange={(event) => setFile(event.target.files?.[0] || null)} className="mt-1 block w-full text-xs text-muted" /></label>}
    </div>}
    {confirming && <p className="mt-4 text-xs text-muted">Review the fields above, then confirm this change.</p>}
    <div className="mt-4 grid grid-cols-2 gap-2"><button type="button" onClick={() => confirming ? setConfirming(false) : onCancel()} className="h-10 rounded-xl border border-divider bg-elevated text-sm font-semibold text-ink">{confirming ? 'Back' : 'Cancel'}</button><button type="submit" disabled={operation !== 'create' && !selectedId} className="h-10 rounded-xl bg-accent text-sm font-semibold text-on-accent disabled:opacity-50">{confirming ? `Confirm ${operation}` : 'Review changes'}</button></div>
  </form>;
}
