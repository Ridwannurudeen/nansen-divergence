"use client";

import { Token } from "@/lib/types";
import { fmtUsd } from "@/lib/utils";
import { ResponsiveContainer, Treemap } from "recharts";

const PHASE_COLORS: Record<string, string> = {
  ACCUMULATION: "#4ade80",
  DISTRIBUTION: "#f43f5e",
  MARKUP: "#6366f1",
  MARKDOWN: "#facc15",
};

interface TreemapContent {
  x: number;
  y: number;
  width: number;
  height: number;
  name: string;
  phase: string;
  value: number;
}

function CustomContent(props: TreemapContent) {
  const { x, y, width, height, name, phase } = props;
  if (width < 30 || height < 20) return null;
  return (
    <g>
      <rect
        x={x}
        y={y}
        width={width}
        height={height}
        fill={PHASE_COLORS[phase] || "#2a2a2a"}
        fillOpacity={0.25}
        stroke="#2a2a2a"
        strokeWidth={1}
      />
      {width > 50 && height > 30 && (
        <>
          <text x={x + 6} y={y + 16} fill={PHASE_COLORS[phase] || "#d4d4d4"} fontSize={12} fontFamily="JetBrains Mono">
            {name}
          </text>
          {width > 70 && height > 45 && (
            <text x={x + 6} y={y + 30} fill="#737373" fontSize={10} fontFamily="JetBrains Mono">
              {fmtUsd(props.value)}
            </text>
          )}
        </>
      )}
    </g>
  );
}

interface HeatMapProps {
  results: Token[];
}

export function HeatMap({ results }: HeatMapProps) {
  const data = results
    .filter((r) => r.market_cap > 0)
    .map((r) => ({
      name: r.token_symbol,
      value: r.market_cap,
      phase: r.phase,
    }))
    .sort((a, b) => b.value - a.value)
    .slice(0, 40);

  if (data.length === 0) return null;

  return (
    <div className="bg-surface border border-border rounded-lg p-4">
      <h2 className="font-mono font-bold text-sm text-muted mb-3">DIVERGENCE HEAT MAP</h2>
      <div className="flex gap-4 mb-3 text-xs font-mono">
        {Object.entries(PHASE_COLORS).map(([phase, color]) => (
          <div key={phase} className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-sm" style={{ backgroundColor: color, opacity: 0.6 }} />
            <span className="text-muted">{phase}</span>
          </div>
        ))}
      </div>
      <ResponsiveContainer width="100%" height={280}>
        <Treemap
          data={data}
          dataKey="value"
          aspectRatio={4 / 3}
          content={<CustomContent x={0} y={0} width={0} height={0} name="" phase="" value={0} />}
        />
      </ResponsiveContainer>
    </div>
  );
}
