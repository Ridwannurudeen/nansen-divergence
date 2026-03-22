import { cn } from "@/lib/utils";

const PHASE_STYLES: Record<string, string> = {
  ACCUMULATION: "bg-bullish/20 text-bullish border-bullish/30",
  DISTRIBUTION: "bg-bearish/20 text-bearish border-bearish/30",
  MARKUP: "bg-neutral/20 text-neutral border-neutral/30",
  MARKDOWN: "bg-warning/20 text-warning border-warning/30",
};

const CONF_STYLES: Record<string, string> = {
  HIGH: "bg-bullish text-bg",
  MEDIUM: "bg-accent text-bg",
  LOW: "bg-border text-muted",
};

interface BadgeProps {
  children: React.ReactNode;
  variant?: "phase" | "confidence" | "default";
  value?: string;
  className?: string;
}

export function Badge({ children, variant = "default", value, className }: BadgeProps) {
  let variantClass = "bg-surface text-muted border border-border";

  if (variant === "phase" && value) {
    variantClass = PHASE_STYLES[value] || variantClass;
    variantClass += " border";
  } else if (variant === "confidence" && value) {
    variantClass = CONF_STYLES[value] || variantClass;
  }

  return (
    <span className={cn("text-xs px-2 py-0.5 rounded font-mono font-bold inline-block", variantClass, className)}>
      {children}
    </span>
  );
}
