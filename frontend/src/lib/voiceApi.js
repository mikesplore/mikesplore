const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

async function fetchJson(path, signal) {
  const response = await fetch(`${API_BASE_URL}${path}`, { signal });
  if (!response.ok) throw new Error(`Voice API request failed (${response.status})`);
  return response.json();
}

// Used only for the voice app's dynamic favicon/profile-media setup.
export function fetchAssets(signal) {
  return fetchJson('/assets', signal);
}
