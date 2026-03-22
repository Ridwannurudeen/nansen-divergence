const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

async function fetcher<T>(url: string): Promise<T> {
  const res = await fetch(`${API_BASE}${url}`);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export { fetcher, API_BASE };
