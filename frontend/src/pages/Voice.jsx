import { useEffect, useRef, useState } from 'react';
import PinPad from '../aui/PinPad';
import OwnerModeBadge from '../aui/OwnerModeBadge';
import OwnerSessionExpired from '../aui/OwnerSessionExpired';
import OperationSuccess from '../aui/OperationSuccess';
import MediaDropzone from '../aui/MediaDropzone';
import MediaUploadProgress from '../aui/MediaUploadProgress';
import MediaReplaceCard from '../aui/MediaReplaceCard';
import ConnectionAlert from '../aui/ConnectionAlert';
import ProjectResultStrip from '../aui/ProjectResultStrip';
import VoiceOrb from '../aui/VoiceOrb';
import ThemeToggle from '../components/ThemeToggle';
import ProfileEditForm from '../aui/ProfileEditForm';
import OwnerResourceForm from '../aui/OwnerResourceForm';

function pcm16(float32) {
  const buffer = new ArrayBuffer(float32.length * 2);
  const view = new DataView(buffer);
  for (let i = 0; i < float32.length; i += 1) {
    const sample = Math.max(-1, Math.min(1, float32[i]));
    view.setInt16(i * 2, sample < 0 ? sample * 0x8000 : sample * 0x7fff, true);
  }
  return buffer;
}

function resampleTo24k(input, sourceRate) {
  if (sourceRate === 24000) return input;
  const ratio = sourceRate / 24000;
  const output = new Float32Array(Math.max(1, Math.round(input.length / ratio)));
  for (let index = 0; index < output.length; index += 1) {
    const sourceIndex = index * ratio;
    const left = Math.floor(sourceIndex);
    const right = Math.min(left + 1, input.length - 1);
    const amount = sourceIndex - left;
    output[index] = input[left] * (1 - amount) + input[right] * amount;
  }
  return output;
}

export default function Voice() {
  const [state, setState] = useState('idle');
  const [voiceIntensity, setVoiceIntensity] = useState(0);
  const [error, setError] = useState('');
  const [actions, setActions] = useState([]);
  const [pin, setPin] = useState('');
  const [pinPrompt, setPinPrompt] = useState(null);
  const [ownerUnlocked, setOwnerUnlocked] = useState(false);
  const [ownerExpired, setOwnerExpired] = useState(false);
  const [operation, setOperation] = useState(null);
  const [uploadRequested, setUploadRequested] = useState(false);
  const [uploadType, setUploadType] = useState('profile-image');
  const [uploadProgress, setUploadProgress] = useState(null);
  const [uploadFile, setUploadFile] = useState(null);
  const [pendingUploadFile, setPendingUploadFile] = useState(null);
  const [ownerAction, setOwnerAction] = useState('');
  const [profileDraft, setProfileDraft] = useState({});
  const [sheetExpanded, setSheetExpanded] = useState(false);
  const [sheetDismissed, setSheetDismissed] = useState(false);
  const [sheetMounted, setSheetMounted] = useState(false);
  const [sheetOpen, setSheetOpen] = useState(false);
  const socket = useRef(null);
  const capture = useRef(null);
  const processor = useRef(null);
  const intensityFrame = useRef(null);
  const endingConversation = useRef(false);

  useEffect(() => {
    setSheetDismissed(false);
  }, [actions.length, pinPrompt, uploadRequested, pendingUploadFile, uploadProgress, operation, error, ownerExpired, ownerUnlocked]);

  function updateVoiceIntensity(samples) {
    let sum = 0;
    for (let index = 0; index < samples.length; index += 1) sum += samples[index] * samples[index];
    const rms = Math.min(1, Math.sqrt(sum / samples.length) * 4);
    if (intensityFrame.current) return;
    intensityFrame.current = requestAnimationFrame(() => {
      setVoiceIntensity(rms);
      intensityFrame.current = null;
    });
  }

  function displayItem(item) {
    setActions((current) => current.some((entry) => (entry.url && item.url && entry.url === item.url) || (entry.slug && item.slug && entry.slug === item.slug) || (!entry.url && !item.url && entry.label === item.label)) ? current : [...current, item]);
  }

  function actionGroups() {
    const groups = new Map();
    actions.forEach((action) => {
      if (action.type !== 'display_item') return;
      const key = action.type === 'display_item'
        ? (action.item_type === 'profile' || action.item_type === 'profile-image' ? 'Profile' : action.item_type === 'contact-link' ? 'Contact' : action.item_type === 'cv' ? 'Documents' : action.item_type === 'bucket-list' ? 'Bucket list' : 'Media')
        : (action.item_type === 'project' ? 'Projects' : action.item_type === 'article' ? 'Articles' : 'Related links');
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push(action);
    });
    return [...groups.entries()];
  }

  function pickMedia(item) {
    if (item?.url) window.open(item.url, '_blank', 'noopener,noreferrer');
  }

  function backendUrl() {
    const protocol = window.location.protocol === 'https:' ? 'https:' : 'http:';
    return import.meta.env.VITE_API_BASE_URL || `${protocol}//${window.location.host}`;
  }

  async function submitPin(pinValue = pin) {
    if (!pinValue) return;
    const response = await fetch(`${backendUrl()}/owner/unlock`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pin: pinValue }),
    });
    const result = await response.json().catch(() => ({}));
    if (!response.ok) {
      setPinPrompt({ ...(pinPrompt || {}), error: result.detail || 'Owner unlock failed.' });
      setPin('');
      return;
    }
    const requestedAction = pinPrompt?.action || '';
    sessionStorage.setItem('owner_session', result.owner_session);
    setPin('');
    setPinPrompt(null);
    setOwnerExpired(false);
    setOwnerUnlocked(true);
    setOwnerAction(requestedAction);
    if (/update.*(name|profile|tagline|location|focus|experience|availability|about)|change.*(name|profile|tagline|location|focus|experience|availability|about)/i.test(requestedAction)) {
      fetch(`${backendUrl()}/profile`).then((profileResponse) => profileResponse.ok ? profileResponse.json() : {}).then(setProfileDraft).catch(() => {});
    }
    if (/profile\s+picture|profile\s+photo/i.test(requestedAction)) { setUploadType('profile-image'); setUploadRequested(true); }
    if (/\bcv\b|resume/i.test(requestedAction)) { setUploadType('cv'); setUploadRequested(true); }
    if (socket.current?.readyState === WebSocket.OPEN) socket.current.send(JSON.stringify({ type: 'owner_session', token: result.owner_session }));
  }

  async function saveProfile(update) {
    const token = sessionStorage.getItem('owner_session');
    const response = await fetch(`${backendUrl()}/profile`, { method: 'PATCH', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` }, body: JSON.stringify(update) });
    if (response.status === 401) { setOwnerUnlocked(false); setOwnerExpired(true); sessionStorage.removeItem('owner_session'); return; }
    if (!response.ok) { setError('The profile could not be updated.'); return; }
    setOwnerAction('');
    setOperation({ title: 'Profile updated', message: 'Live on mikesplore.me now' });
  }

  async function saveOwnerResource(resource, payload) {
    const token = sessionStorage.getItem('owner_session');
    const resourceName = resource === 'project' ? 'projects' : resource === 'certificate' ? 'certificates' : resource === 'link' ? 'links' : resource === 'skill' ? 'skills' : resource === 'bucket-list' ? 'bucket-list' : 'education';
    if (resource === 'certificate' && payload.file) {
      const body = new FormData();
      body.append('title', payload.title || 'Certificate');
      body.append('file', payload.file);
      const uploadResponse = await fetch(`${backendUrl()}/certificates`, { method: 'POST', headers: { Authorization: `Bearer ${token}` }, body });
      if (!uploadResponse.ok) { setError('The certificate could not be uploaded.'); return; }
      setOwnerAction('');
      setOperation({ title: 'Certificate uploaded', message: 'Live on mikesplore.me now' });
      return;
    }
    if (resource === 'project' && payload.action === 'create') payload = { ...payload, content_type: 'project', is_visible: true, is_featured: false, custom_order: 0, tags: [], source: {} };
    const response = await fetch(`${backendUrl()}/owner/resources/${resourceName}`, { method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` }, body: JSON.stringify(payload) });
    if (response.status === 401) { setOwnerUnlocked(false); setOwnerExpired(true); sessionStorage.removeItem('owner_session'); return; }
    if (!response.ok) { setError(`The ${resource} could not be saved.`); return; }
    setOwnerAction('');
    setOperation({ title: `${resource[0].toUpperCase()}${resource.slice(1)} saved`, message: 'Live on mikesplore.me now' });
  }

  function selectProfileImage(file) {
    if (!file) return;
    const validFile = uploadType === 'cv' ? file.type === 'application/pdf' : ['image/jpeg', 'image/png'].includes(file.type);
    if (!validFile || file.size > 5 * 1024 * 1024) {
      setError(uploadType === 'cv' ? 'Choose a readable PDF up to 5MB.' : 'Choose a JPG or PNG image up to 5MB.');
      return;
    }
    setError('');
    setPendingUploadFile(file);
  }

  async function uploadProfileImage() {
    const file = pendingUploadFile;
    if (!file) return;
    const token = sessionStorage.getItem('owner_session');
    if (!token) { setOwnerUnlocked(false); setOwnerExpired(true); return; }
    setError('');
    setUploadFile(file);
    setUploadProgress(0);
    const body = new FormData();
    body.append('asset_type', uploadType);
    body.append('label', file.name);
    body.append('file', file);
    const xhr = new XMLHttpRequest();
    xhr.open('POST', `${backendUrl()}/assets`);
    xhr.setRequestHeader('Authorization', `Bearer ${token}`);
    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) setUploadProgress(Math.round((event.loaded / event.total) * 100));
    };
    xhr.onload = () => {
      setUploadProgress(null);
      if (xhr.status === 401) { setOwnerUnlocked(false); setOwnerExpired(true); sessionStorage.removeItem('owner_session'); return; }
      if (xhr.status < 200 || xhr.status >= 300) { setError('The profile picture could not be updated.'); return; }
      setUploadRequested(false);
      setPendingUploadFile(null);
      setOperation({ title: uploadType === 'cv' ? 'CV replaced' : 'Profile photo updated', message: 'Live on mikesplore.me now' });
    };
    xhr.onerror = () => { setUploadProgress(null); setError('The upload failed. Check your connection and try again.'); };
    xhr.send(body);
  }

  async function lockOwner() {
    const token = sessionStorage.getItem('owner_session');
    await fetch(`${backendUrl()}/owner/lock`, { method: 'POST', headers: token ? { Authorization: `Bearer ${token}` } : {} });
    sessionStorage.removeItem('owner_session');
    setOwnerUnlocked(false);
    if (socket.current?.readyState === WebSocket.OPEN) socket.current.send(JSON.stringify({ type: 'owner_session', token: '' }));
  }

  useEffect(() => () => stop(), []);

  function playAudio(encoded) {
    if (!encoded) return;
    const bytes = Uint8Array.from(atob(encoded), (character) => character.charCodeAt(0));
    const view = new DataView(bytes.buffer);
    const samples = new Float32Array(Math.floor(bytes.byteLength / 2));
    for (let index = 0; index < samples.length; index += 1) samples[index] = view.getInt16(index * 2, true) / 32768;
    updateVoiceIntensity(samples);
    const context = capture.current?.context;
    if (!context) return;
    const buffer = context.createBuffer(1, samples.length, 24000);
    buffer.copyToChannel(samples, 0);
    const source = context.createBufferSource();
    source.buffer = buffer;
    source.connect(context.destination);
    // Keep a short cushion between network delivery and playback so uneven
    // WebSocket chunk timing doesn't turn into clicks or audible gaps.
    const startAt = Math.max(context.currentTime + 0.08, capture.current.nextAudioTime || 0);
    source.start(startAt);
    capture.current.nextAudioTime = startAt + buffer.duration;
    setState('speaking');
    source.onended = () => {
      if (context.currentTime >= (capture.current?.nextAudioTime || 0) - 0.02) {
        setState('listening');
        if (endingConversation.current) stop();
      }
    };
  }

  async function start() {
    setError(''); setActions([]);
    endingConversation.current = false;
    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const apiBase = import.meta.env.VITE_API_BASE_URL || `${protocol}://${window.location.host}`;
    const voiceBase = import.meta.env.VITE_VOICE_API_BASE_URL || apiBase;
    const backend = new URL(voiceBase);
    const wsProtocol = backend.protocol === 'https:' ? 'wss:' : 'ws:';
    const ws = new WebSocket(`${wsProtocol}//${backend.host}/ws/voice`);
    socket.current = ws;
    ws.onmessage = async (event) => {
      const message = JSON.parse(event.data);
      if (message.type === 'error') { setError(message.message); setState('error'); }
      if (message.type === 'pin_required') setPinPrompt({ title: message.title, attemptsLeft: message.attempts_left, action: message.action || '' });
      if (message.type === 'owner_unlocked') { setOwnerUnlocked(true); setPinPrompt(null); }
      if (message.type === 'owner_locked') { setOwnerUnlocked(false); sessionStorage.removeItem('owner_session'); }
      if (message.type === 'owner_session_expired') { setOwnerUnlocked(false); setOwnerExpired(true); sessionStorage.removeItem('owner_session'); }
      if (message.type === 'upload_requested') setUploadRequested(true);
      if (message.type === 'operation_succeeded') setOperation({ title: message.title, message: message.message });
      if (message.type === 'operation_failed') setError(message.message || 'The operation failed.');
      if (message.type === 'ready') setState('listening');
      if (message.type === 'listening') {
        if (ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: 'interrupt' }));
        setState('listening');
      }
      if (message.type === 'thinking') setState('thinking');
      if (message.type === 'transcript') {
        if (message.final) {
          setActions([]);
          if (/\b(end|stop|close|finish)\b.*\b(conversation|session|chat|talking)\b/i.test(message.text || '')) {
            // Let AssemblyAI produce the final acknowledgement. The session
            // closes from the last response audio's onended callback.
            endingConversation.current = true;
          }
        }
      }
      if (message.type === 'audio') playAudio(message.audio);
      if (message.type === 'actions') (message.items || []).forEach((item) => item.type === 'display_item' ? displayItem(item) : setActions((current) => [...current, item]));
    };
    ws.onerror = () => { setError('Voice connection failed.'); setState('error'); };
    ws.onclose = () => { if (state !== 'error') setState('idle'); };
    await new Promise((resolve) => {
      ws.onopen = () => {
        const existingOwnerSession = sessionStorage.getItem('owner_session');
        if (existingOwnerSession) ws.send(JSON.stringify({ type: 'owner_session', token: existingOwnerSession }));
        resolve();
      };
    });
    const stream = await navigator.mediaDevices.getUserMedia({ audio: {
      channelCount: 1,
      echoCancellation: true,
      noiseSuppression: true,
      autoGainControl: true,
      sampleRate: 24000,
    } });
    const context = new AudioContext({ sampleRate: 24000, sinkId: 'default' });
    await context.resume();
    const source = context.createMediaStreamSource(stream);
    const node = context.createScriptProcessor(2048, 1, 1);
    const muteOutput = context.createGain();
    muteOutput.gain.value = 0;
    node.onaudioprocess = (event) => {
      if (ws.readyState === WebSocket.OPEN) {
        const samples = resampleTo24k(event.inputBuffer.getChannelData(0), context.sampleRate);
        updateVoiceIntensity(samples);
        ws.send(pcm16(samples));
      }
    };
    // ScriptProcessorNode must be connected to an active graph for
    // onaudioprocess to run. A zero-gain output keeps the graph alive without
    // routing microphone audio back through the phone/desktop speakers.
    source.connect(node);
    node.connect(muteOutput);
    muteOutput.connect(context.destination);
    capture.current = { stream, context, nextAudioTime: 0 };
    processor.current = node;
  }

  function stop() {
    if (socket.current?.readyState === WebSocket.OPEN) socket.current.send(JSON.stringify({ type: 'stop' }));
    socket.current?.close(); socket.current = null;
    capture.current?.context?.suspend?.();
    processor.current?.disconnect(); processor.current = null;
    capture.current?.stream?.getTracks().forEach((track) => track.stop());
    capture.current?.context?.close?.(); capture.current = null;
    setState('idle');
    setVoiceIntensity(0);
    endingConversation.current = false;
  }

  const hasSheetContent = Boolean(
    actions.length || pinPrompt || uploadRequested || pendingUploadFile || ownerAction ||
    uploadProgress !== null || operation || error || ownerExpired || ownerUnlocked,
  );
  const projectActions = actions.filter((action) => action.type === 'open_resource' && action.item_type === 'project');
  const linkActions = actions.filter((action) => action.type === 'open_resource' && action.item_type !== 'project');

  useEffect(() => {
    if (hasSheetContent && !sheetDismissed) {
      setSheetMounted(true);
      requestAnimationFrame(() => setSheetOpen(true));
      return undefined;
    }
    setSheetOpen(false);
    const timeout = window.setTimeout(() => setSheetMounted(false), 300);
    return () => window.clearTimeout(timeout);
  }, [hasSheetContent, sheetDismissed]);

  return <main className={`relative mx-auto flex min-h-screen w-full max-w-2xl flex-col items-center justify-center px-6 pb-8 text-center transition-[padding] duration-300 lg:max-w-none ${hasSheetContent && !sheetDismissed ? 'lg:pr-[clamp(22rem,34vw,42rem)]' : ''}`}>
    <div className="fixed right-5 top-5 z-30"><ThemeToggle /></div>
    <h1 className="mb-4 text-4xl font-bold">Milo</h1>
    <p className="mb-8 max-w-lg text-base text-muted">Ask Milo about Mike’s work.</p>
    <div className="mb-8"><VoiceOrb active={(state === 'listening' || state === 'speaking') && voiceIntensity > 0.04} mode={state} intensity={voiceIntensity} showLabel={false} /></div>
    <button type="button" onClick={state === 'idle' || state === 'error' ? start : stop} className="rounded-full bg-accent px-8 py-4 font-semibold text-on-accent shadow-lg">
      {state === 'idle' || state === 'error' ? 'Start talking' : 'Stop'}
    </button>

    {sheetMounted && <aside className={`fixed inset-x-0 bottom-0 z-20 overflow-y-auto rounded-t-3xl border-t border-divider bg-page/95 px-5 pb-8 pt-4 text-center shadow-2xl backdrop-blur transition-[max-height,transform] duration-300 sm:inset-x-auto sm:left-1/2 sm:w-full sm:max-w-2xl sm:-translate-x-1/2 lg:inset-y-0 lg:right-0 lg:bottom-auto lg:left-auto lg:h-screen lg:max-h-none lg:w-[clamp(22rem,34vw,42rem)] lg:max-w-none lg:rounded-none lg:rounded-l-3xl lg:border-l lg:border-t-0 lg:px-7 lg:pt-7 lg:transition-transform ${sheetOpen ? 'lg:translate-x-0' : 'lg:translate-x-full'} ${sheetExpanded ? 'max-h-[94vh]' : 'max-h-[72vh]'}`}>
      <div className="relative mb-5">
        <button type="button" onClick={() => setSheetExpanded((expanded) => !expanded)} className="mx-auto block h-1 w-10 rounded-full bg-divider lg:hidden" aria-label={sheetExpanded ? 'Collapse details' : 'Expand details'} />
        <div className="hidden text-left text-xs font-semibold uppercase tracking-[0.2em] text-muted lg:block">Details</div>
        <button type="button" onClick={() => { setSheetDismissed(true); setSheetExpanded(false); }} className="absolute right-0 top-1/2 -translate-y-1/2 text-lg leading-none text-muted hover:text-ink" aria-label="Dismiss details">×</button>
      </div>
      {(projectActions.length > 0 || linkActions.length > 0) && <div className="mb-5"><ProjectResultStrip projects={projectActions.map((action) => ({ title: action.label, url: action.url, summary: action.summary, imageUrl: action.image_url }))} links={linkActions.map((action) => ({ label: action.label, url: action.url, summary: action.summary, imageUrl: action.image_url }))} /></div>}
      {actions.some((action) => action.type === 'display_item') && <div className="mx-auto w-full max-w-2xl space-y-6 text-left">
        {actionGroups().map(([group, items]) => <section key={group}>
          <div className="mb-3 flex items-center justify-between"><h2 className="text-xs font-semibold uppercase tracking-[0.2em] text-muted">{group}</h2><span className="text-xs text-muted">{items.length} {items.length === 1 ? 'item' : 'items'}</span></div>
          <div className={items.length === 1 ? 'flex justify-center' : 'grid grid-cols-2 gap-3 sm:grid-cols-3'}>{items.map((action) => <button type="button" key={`${action.label}-${action.url || action.slug || action.item_type}`} onClick={() => pickMedia(action)} className={`${action.item_type === 'profile' ? 'w-full max-w-xl' : action.item_type === 'profile-image' ? 'w-full max-w-xs' : items.length === 1 ? 'w-full max-w-sm' : 'w-full'} overflow-hidden rounded-2xl border border-divider bg-card text-left shadow-sm transition hover:-translate-y-0.5 hover:border-primary hover:shadow-md`}>{action.item_type === 'profile' ? <div className="p-5"><div className="flex items-start justify-between gap-3"><div><div className="text-lg font-semibold text-ink">{action.label}</div>{action.summary && <div className="mt-1 text-sm text-muted">{action.summary}</div>}</div>{action.status && <span className="rounded-full bg-accent/10 px-2.5 py-1 text-[11px] font-semibold text-accent">{action.status}</span>}</div>{action.location && <div className="mt-3 text-xs text-muted">{action.location}</div>}{action.description && <p className="mt-4 text-sm leading-6 text-muted">{action.description}</p>}</div> : action.item_type === 'contact-link' ? <div className="flex min-h-24 items-center gap-3 p-4"><div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-accent/10 text-accent">↗</div><div className="min-w-0"><div className="truncate text-sm font-semibold text-ink">{action.label}</div>{action.summary && <div className="mt-1 truncate text-xs text-muted">{action.summary}</div>}</div></div> : action.item_type === 'bucket-list' ? <div className="min-h-28 p-4"><div className="text-sm font-semibold text-ink">{action.done ? '✓ ' : '○ '}{action.label}</div>{action.description && <div className="mt-2 text-xs text-muted">{action.description}</div>}</div> : action.item_type === 'cv' ? <div className="flex h-40 items-center justify-center bg-black/5 text-5xl">📄</div> : action.item_type === 'open_resource' ? <div className="min-h-28 p-4"><div className="text-sm font-semibold text-ink">{action.label}</div>{action.summary && <div className="mt-2 line-clamp-3 text-xs leading-5 text-muted">{action.summary}</div>}{action.url && <div className="mt-3 text-xs font-medium text-nav">Open resource ↗</div>}</div> : <div className={`${action.item_type === 'profile-image' ? 'aspect-square' : items.length === 1 ? 'h-56' : 'h-32'} bg-black/5`}><img src={action.url} alt={action.label} className={`${action.item_type === 'profile-image' ? 'h-full w-full object-contain p-3' : 'h-full w-full object-cover'}`} /></div>}<span className="block truncate px-4 py-3 text-sm font-medium text-ink">{action.label}</span></button>)}</div>
        </section>)}
      </div>}
      {ownerUnlocked && <div className="mt-5"><OwnerModeBadge active onLock={lockOwner} /></div>}
      {ownerUnlocked && /update.*(name|profile|tagline|location|focus|experience|availability|about)|change.*(name|profile|tagline|location|focus|experience|availability|about)/i.test(ownerAction) && <div className="mt-5"><ProfileEditForm initialProfile={profileDraft} onSave={saveProfile} onCancel={() => setOwnerAction('')} /></div>}
      {ownerUnlocked && /project/i.test(ownerAction) && <div className="mt-5"><OwnerResourceForm resource="project" resourceKey="projects" token={sessionStorage.getItem('owner_session')} apiBase={backendUrl()} onSave={(payload) => saveOwnerResource('project', payload)} onCancel={() => setOwnerAction('')} /></div>}
      {ownerUnlocked && /certificate/i.test(ownerAction) && <div className="mt-5"><OwnerResourceForm resource="certificate" resourceKey="certificates" token={sessionStorage.getItem('owner_session')} apiBase={backendUrl()} onSave={(payload) => saveOwnerResource('certificate', payload)} onCancel={() => setOwnerAction('')} /></div>}
      {ownerUnlocked && /link|contact/i.test(ownerAction) && <div className="mt-5"><OwnerResourceForm resource="link" resourceKey="links" token={sessionStorage.getItem('owner_session')} apiBase={backendUrl()} onSave={(payload) => saveOwnerResource('link', payload)} onCancel={() => setOwnerAction('')} /></div>}
      {ownerUnlocked && /skill/i.test(ownerAction) && <div className="mt-5"><OwnerResourceForm resource="skill" resourceKey="skills" token={sessionStorage.getItem('owner_session')} apiBase={backendUrl()} onSave={(payload) => saveOwnerResource('skill', payload)} onCancel={() => setOwnerAction('')} /></div>}
      {ownerUnlocked && /education|school|degree/i.test(ownerAction) && <div className="mt-5"><OwnerResourceForm resource="education" resourceKey="education" token={sessionStorage.getItem('owner_session')} apiBase={backendUrl()} onSave={(payload) => saveOwnerResource('education', payload)} onCancel={() => setOwnerAction('')} /></div>}
      {ownerUnlocked && /bucket/i.test(ownerAction) && <div className="mt-5"><OwnerResourceForm resource="bucket-list" resourceKey="bucket-list" token={sessionStorage.getItem('owner_session')} apiBase={backendUrl()} onSave={(payload) => saveOwnerResource('bucket-list', payload)} onCancel={() => setOwnerAction('')} /></div>}
      {ownerExpired && <div className="mt-5"><OwnerSessionExpired /></div>}
      {pinPrompt && <div className="mt-5"><PinPad title={pinPrompt.title} value={pin} attemptsLeft={pinPrompt.attemptsLeft} error={pinPrompt.error} onChange={(next) => { setPin(next); if (next.length === 4) submitPin(next); }} onCancel={() => { setPin(''); setPinPrompt(null); }} /></div>}
      {uploadRequested && ownerUnlocked && !uploadProgress && !pendingUploadFile && <div className="mt-5"><MediaDropzone onChoose={selectProfileImage} onDrop={selectProfileImage} accept={uploadType === 'cv' ? 'application/pdf' : 'image/jpeg,image/png'} title={uploadType === 'cv' ? 'Drop a CV here, or tap to choose one' : 'Drop an image here, or tap to choose one'} hint={uploadType === 'cv' ? 'PDF, up to 5MB' : 'JPG or PNG, up to 5MB'} /></div>}
      {pendingUploadFile && !uploadProgress && <div className="mt-5"><MediaReplaceCard fileName={pendingUploadFile.name} fileSizeBytes={pendingUploadFile.size} previewUrl={uploadType === 'profile-image' ? URL.createObjectURL(pendingUploadFile) : ''} actionLabel={uploadType === 'cv' ? 'Replace CV' : 'Replace photo'} onCancel={() => setPendingUploadFile(null)} onReplace={uploadProfileImage} /></div>}
      {uploadProgress !== null && <div className="mt-5"><MediaUploadProgress fileName={uploadFile?.name} fileSizeBytes={uploadFile?.size} progress={uploadProgress} /></div>}
      {operation && <div className="mt-5"><OperationSuccess title={operation.title} message={operation.message} /></div>}
      {error && <div className="mt-5"><ConnectionAlert title="Voice session issue" message={error} /></div>}
    </aside>}
  </main>;
}
