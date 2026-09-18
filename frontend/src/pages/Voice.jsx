import { useEffect, useRef, useState } from 'react';

function pcm16(float32) {
  const buffer = new ArrayBuffer(float32.length * 2);
  const view = new DataView(buffer);
  for (let i = 0; i < float32.length; i += 1) {
    const sample = Math.max(-1, Math.min(1, float32[i]));
    view.setInt16(i * 2, sample < 0 ? sample * 0x8000 : sample * 0x7fff, true);
  }
  return buffer;
}

export default function Voice() {
  const [state, setState] = useState('idle');
  const [transcript, setTranscript] = useState('');
  const [response, setResponse] = useState('');
  const [error, setError] = useState('');
  const socket = useRef(null);
  const capture = useRef(null);
  const playback = useRef(null);
  const processor = useRef(null);
  const chunks = useRef([]);

  useEffect(() => () => stop(), []);

  function playAudio(base64) {
    chunks.current.push(Uint8Array.from(atob(base64), (char) => char.charCodeAt(0)));
    if (state !== 'speaking') setState('speaking');
  }

  async function start() {
    setError(''); setTranscript(''); setResponse('');
    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const apiBase = import.meta.env.VITE_API_BASE_URL || `${protocol}://${window.location.host}`;
    const backend = new URL(apiBase);
    const wsProtocol = backend.protocol === 'https:' ? 'wss:' : 'ws:';
    const ws = new WebSocket(`${wsProtocol}//${backend.host}/ws/voice`);
    socket.current = ws;
    ws.onmessage = async (event) => {
      const message = JSON.parse(event.data);
      if (message.type === 'error') { setError(message.message); setState('error'); }
      if (message.type === 'ready' || message.type === 'listening') setState('listening');
      if (message.type === 'thinking') setState('thinking');
      if (message.type === 'transcript') setTranscript(message.text);
      if (message.type === 'response') setResponse(message.text);
      if (message.type === 'audio') playAudio(message.data);
      if (message.type === 'speech_finished') {
        const blob = new Blob(chunks.current, { type: 'audio/mpeg' });
        chunks.current = [];
        const url = URL.createObjectURL(blob);
        playback.current = new Audio(url);
        playback.current.onended = () => { URL.revokeObjectURL(url); setState('listening'); };
        await playback.current.play();
      }
    };
    ws.onerror = () => { setError('Voice connection failed.'); setState('error'); };
    ws.onclose = () => { if (state !== 'error') setState('idle'); };
    await new Promise((resolve) => { ws.onopen = resolve; });
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const context = new AudioContext({ sampleRate: 16000 });
    const source = context.createMediaStreamSource(stream);
    const node = context.createScriptProcessor(4096, 1, 1);
    node.onaudioprocess = (event) => { if (ws.readyState === WebSocket.OPEN) ws.send(pcm16(event.inputBuffer.getChannelData(0))); };
    source.connect(node); node.connect(context.destination);
    capture.current = { stream, context };
    processor.current = node;
  }

  function stop() {
    if (socket.current?.readyState === WebSocket.OPEN) socket.current.send(JSON.stringify({ type: 'stop' }));
    socket.current?.close(); socket.current = null;
    processor.current?.disconnect(); processor.current = null;
    capture.current?.stream?.getTracks().forEach((track) => track.stop());
    capture.current?.context?.close?.(); capture.current = null;
    playback.current?.pause?.(); playback.current = null;
    chunks.current = []; setState('idle');
  }

  return <main className="mx-auto flex min-h-[70vh] max-w-2xl flex-col items-center justify-center px-6 text-center">
    <p className="mb-3 text-sm uppercase tracking-[0.3em] text-primary">Talk to Mike</p>
    <h1 className="mb-4 text-4xl font-bold">Mike’s voice representative</h1>
    <p className="mb-8 max-w-lg text-gray-500">Ask a question naturally. The first version is focused on making the voice loop feel fast and reliable.</p>
    <button type="button" onClick={state === 'idle' || state === 'error' ? start : stop} className="rounded-full bg-primary px-8 py-4 font-semibold text-white shadow-lg">
      {state === 'idle' || state === 'error' ? 'Start talking' : 'Stop'}
    </button>
    <p className="mt-5 text-sm capitalize text-gray-500">{state}</p>
    {transcript && <p className="mt-8 max-w-xl italic">“{transcript}”</p>}
    {response && <p className="mt-4 max-w-xl">{response}</p>}
    {error && <p className="mt-4 text-red-600">{error}</p>}
  </main>;
}
