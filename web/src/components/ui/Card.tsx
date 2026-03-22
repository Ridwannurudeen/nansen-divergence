import { cn } from "@/lib/utils";

interface CardProps {
  children: React.ReactNode;
  className?: string;
  glow?: "green" | "red" | null;
}

export function Card({ children, className, glow }: CardProps) {
  return (
    <div
      className={cn(
        "bg-surface border border-border rounded-lg p-4",
        glow === "green" && "glow-box-green border-bullish/30",
        glow === "red" && "glow-box-red border-bearish/30",
        className,
      )}
    >
      {children}
    </div>
  );
}

export function CardHeader({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={cn("text-xs font-mono text-muted uppercase tracking-wider mb-1", className)}>
      {children}
    </div>
  );
}

export function CardValue({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={cn("text-2xl font-mono font-bold", className)}>
      {children}
    </div>
  );
}
