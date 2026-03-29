"use client";

const STORAGE_KEY = "nansen-api-key";

export function getApiKey(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return localStorage.getItem(STORAGE_KEY) || null;
  } catch {
    return null;
  }
}

export function saveApiKey(key: string): void {
  localStorage.setItem(STORAGE_KEY, key.trim());
  window.dispatchEvent(new Event("apikey-change"));
}

export function clearApiKey(): void {
  localStorage.removeItem(STORAGE_KEY);
  window.dispatchEvent(new Event("apikey-change"));
}
