"use client";

const STORAGE_KEY = "nansen-watchlist";

export function getWatchlist(): string[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

export function toggleWatchlist(tokenAddress: string): boolean {
  const list = getWatchlist();
  const addr = tokenAddress.toLowerCase();
  const idx = list.indexOf(addr);
  if (idx >= 0) {
    list.splice(idx, 1);
  } else {
    list.push(addr);
  }
  localStorage.setItem(STORAGE_KEY, JSON.stringify(list));
  window.dispatchEvent(new Event("watchlist-change"));
  return idx < 0; // true if added, false if removed
}

export function isWatched(tokenAddress: string): boolean {
  return getWatchlist().includes(tokenAddress.toLowerCase());
}
