"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, Radar, TrendingUp, ArrowRightLeft, Info, Menu, X } from "lucide-react";
import { cn } from "@/lib/utils";

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

  const isActive = (href: string) => {
    if (href === "/") return pathname === "/";
    return pathname.startsWith(href);
  };

  return (
    <nav className="sticky top-0 z-50 bg-bg/90 backdrop-blur-sm border-b border-border">
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
                    : "text-muted hover:text-white hover:bg-surface",
                )}
              >
                <Icon size={14} />
                {label}
              </Link>
            ))}
          </div>

          {/* Live indicator */}
          <div className="hidden md:flex items-center gap-2 text-xs font-mono text-muted">
            <span className="w-2 h-2 rounded-full bg-bullish animate-live" />
            LIVE
          </div>

          {/* Mobile hamburger */}
          <button
            onClick={() => setOpen(!open)}
            className="md:hidden text-muted hover:text-white p-1"
          >
            {open ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>

        {/* Mobile menu */}
        {open && (
          <div className="md:hidden border-t border-border py-2 animate-fade-in">
            {NAV_ITEMS.map(({ href, label, icon: Icon }) => (
              <Link
                key={href}
                href={href}
                onClick={() => setOpen(false)}
                className={cn(
                  "flex items-center gap-2 px-3 py-2 rounded text-sm font-mono",
                  isActive(href) ? "text-accent bg-accent/10" : "text-muted hover:text-white",
                )}
              >
                <Icon size={14} />
                {label}
              </Link>
            ))}
          </div>
        )}
      </div>
    </nav>
  );
}
