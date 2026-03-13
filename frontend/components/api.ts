import { API } from '@/services/api';

type ApiInit = Omit<RequestInit, 'body' | 'method' | 'headers'> & {
  method?: string;
  headers?: Record<string, string>;
  body?: BodyInit | Record<string, unknown> | unknown[] | null;
};

async function api<T>(path: string, init: ApiInit = {}): Promise<T> {
  const method = (init.method || 'GET').toUpperCase();
  const headers = init.headers || {};
  const payload = init.body && typeof init.body === 'object' && !(init.body instanceof FormData) ? init.body : init.body;
  const res = await API.request({
    url: path,
    method,
    data: payload,
    headers,
  });
  return res.data as T;
}

export default api;
