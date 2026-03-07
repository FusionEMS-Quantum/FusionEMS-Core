type ApiInit = Omit<RequestInit, "body"> & {
  body?: BodyInit | Record<string, unknown> | unknown[] | null;
};

async function api<T>(path: string, init: ApiInit = {}): Promise<T> {
  const isProd = process.env.NODE_ENV === "production";

  const base =
      process.env.NEXT_PUBLIC_API_BASE ||
      process.env.NEXT_PUBLIC_BACKEND_URL ||
      process.env.NEXT_PUBLIC_API_URL ||
      process.env.BACKEND_URL ||
      (!isProd ? "http://localhost:8000" : undefined);

  if (!base) {
    throw new Error(
        "Backend base URL is not configured. Set NEXT_PUBLIC_BACKEND_URL (or NEXT_PUBLIC_API_URL / BACKEND_URL) in the runtime environment."
    );
  }

  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  const baseNoTrailing = base.endsWith("/") ? base.slice(0, -1) : base;
  const url = `${baseNoTrailing}${normalizedPath}`;

  const headers = new Headers(init.headers);

  let body = init.body as RequestInit["body"];

  const isPlainObjectBody =
      body != null &&
      !(body instanceof FormData) &&
      !(body instanceof URLSearchParams) &&
      !(body instanceof Blob) &&
      !(body instanceof ArrayBuffer) &&
      typeof body === "object";

  if (isPlainObjectBody) {
    if (!headers.has("content-type")) {
      headers.set("content-type", "application/json");
    }
    body = JSON.stringify(body);
  }

  const res = await fetch(url, {
    ...init,
    body,
    headers,
    cache: "no-store",
  });

  const text = await res.text();

  let data: unknown = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = text || null;
  }

  if (!res.ok) {
    const message =
        (typeof data === "object" &&
            data !== null &&
            ("detail" in data || "message" in data) &&
            (((data as { detail?: string }).detail ||
                (data as { message?: string }).message) as string)) ||
        (typeof data === "string" ? data : null) ||
        `Request failed: ${res.status} ${res.statusText}`;

    throw new Error(message);
  }

  return data as T;
}

export default api;z
