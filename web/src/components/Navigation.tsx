"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, Radar, TrendingUp, ArrowRightLeft, Info, Menu, X, Settings } from "lucide-react";
import { cn } from "@/lib/utils";
import { getApiKey } from "@/lib/settings";
import { ApiKeyModal } from "@/components/ApiKeyModal";

const NAV_ITEMS = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/radar", label: "Radar", icon: Radar },
  { href: "/performance", label: "Performance", icon: TrendingUp },
  { href: "/flows", label: "Flows", icon: ArrowRightLeft },
  { href: "/about", label: "About", icon: Info },
];

export function Navigation() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [hasKey, setHasKey] = useState(() => !!getApiKey());

  useEffect(() => {
    const handler = () => setHasKey(!!getApiKey());
    window.addEventListener("apikey-change", handler);
    return () => window.removeEventListener("apikey-change", handler);
  }, []);

  const isActive = (href: string) => {
    if (href === "/") return pathname === "/";
    return pathname.startsWith(href);
  };

  return (
    <nav className="sticky top-0 z-50 bg-bg/90 backdrop-blur-sm border-b border-border" role="navigation" aria-label="Main navigation">
      <div className="max-w-7xl mx-auto px-4">
        <div className="flex items-center justify-between h-12">
          <Link href="/" className="flex items-center gap-2">
            <span className="font-mono font-bold text-accent text-lg glow-orange">SM</span>
            <span className="font-mono text-muted text-sm hidden sm:inline">DIVERGENCE</span>
          </Link>

          {/* Desktop nav */}
          <div className="hidden md:flex items-center gap-1">
            {NAV_ITEMS.map(({ href, label, icon: Icon }) => (
              <Link
                key={href}
                href={href}
                className={cn(
                  "flex items-center gap-1.5 px-3 py-1.5 rounded text-sm font-mono transition-colors",
                  isActive(href)
                    ? "bg-accent/10 text-accent"
                    : "text-muted hover:text-white hover:bg-surface-hover",
                )}
              >
                <Icon size={14} aria-hidden="true" />
                {label}
              </Link>
            ))}
          </div>

          {/* BYOK + Live indicator */}
          <div className="hidden md:flex items-center gap-3">
            <button
              onClick={() => setShowSettings(true)}
              className={cn(
                "flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-mono font-bold transition-colors border",
                hasKey
                  ? "border-bullish/40 text-bullish bg-bullish/10 hover:bg-bullish/20"
                  : "border-accent/40 text-accent bg-accent/10 hover:bg-accent/20 animate-pulse",
              )}
              aria-label="Bring your own Nansen API key"
            >
              <Settings size={12} aria-hidden="true" />
              {hasKey ? "KEY SET" : "BYOK"}
            </button>
            <div className="flex items-center gap-2 text-xs font-mono text-muted">
              <span className="w-2 h-2 rounded-full bg-bullish animate-live" aria-hidden="true" />
              LIVE
            </div>
          </div>

          {/* Mobile hamburger */}
          <button
            onClick={() => setOpen(!open)}
            className="md:hidden text-muted hover:text-white p-1 transition-colors"
            aria-label={open ? "Close navigation menu" : "Open navigation menu"}
            aria-expanded={open}
          >
            {open ? <X size={20} aria-hidden="true" /> : <Menu size={20} aria-hidden="true" />}
          </button>
        </div>

        {/* Mobile menu */}
        {open && (
          <div className="md:hidden border-t border-border py-2 animate-fade-in" role="menu">
            {NAV_ITEMS.map(({ href, label, icon: Icon }) => (
              <Link
                key={href}
                href={href}
                onClick={() => setOpen(false)}
                className={cn(
                  "flex items-center gap-2 px-3 py-2 rounded text-sm font-mono transition-colors",
                  isActive(href) ? "text-accent bg-accent/10" : "text-muted hover:text-white hover:bg-surface-hover",
                )}
                role="menuitem"
              >
                <Icon size={14} aria-hidden="true" />
                {label}
              </Link>
            ))}
            <button
              onClick={() => { setOpen(false); setShowSettings(true); }}
              className="flex items-center gap-2 px-3 py-2 rounded text-sm font-mono text-muted hover:text-white hover:bg-surface-hover transition-colors w-full"
              role="menuitem"
            >
              <Settings size={14} aria-hidden="true" />
              API Key
              <span
                className={cn(
                  "w-2 h-2 rounded-full ml-auto",
                  hasKey ? "bg-bullish" : "bg-muted/50",
                )}
              />
            </button>
          </div>
        )}
      </div>
      <ApiKeyModal open={showSettings} onClose={() => setShowSettings(false)} />
    </nav>
  );
}
