import { getApiKey } from "@/lib/settings";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

async function fetcher<T>(url: string): Promise<T> {
  const res = await fetch(`${API_BASE}${url}`);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

async function authedFetcher<T>(url: string): Promise<T> {
  const key = getApiKey();
  const opts: RequestInit = {};
  if (key) opts.headers = { "X-Nansen-Key": key };
  const res = await fetch(`${API_BASE}${url}`, opts);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export { fetcher, authedFetcher, API_BASE };
