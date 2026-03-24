export const API_HEADERS = {
  'X-Arthur-Client': 'Arthur-Prime-V1',
};

export const UNAUTHORIZED_EVENT = 'arthur:unauthorized';

export async function apiFetch(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  const res = await fetch(input, init);
  if (res.status === 401 || res.status === 403) {
    localStorage.removeItem('token');
    window.dispatchEvent(new Event(UNAUTHORIZED_EVENT));
  }
  return res;
}
