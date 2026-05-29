"use client";

import {
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Tooltip,
} from "recharts";

interface Props {
  quality: number;
  instruction_adherence: number;
  factual_structural: number;
  tone_format: number;
}

export function ScoreRadar({
  quality,
  instruction_adherence,
  factual_structural,
  tone_format,
}: Props) {
  const data = [
    { dim: "quality", v: quality },
    { dim: "adherence", v: instruction_adherence },
    { dim: "factual", v: factual_structural },
    { dim: "tone", v: tone_format },
  ];
  return (
    <ResponsiveContainer width="100%" height={240}>
      <RadarChart data={data}>
        <PolarGrid stroke="#334155" />
        <PolarAngleAxis dataKey="dim" tick={{ fill: "#94a3b8", fontSize: 11 }} />
        <PolarRadiusAxis
          domain={[0, 5]}
          tickCount={6}
          tick={{ fill: "#64748b", fontSize: 10 }}
        />
        <Radar
          name="rubrica"
          dataKey="v"
          stroke="#60a5fa"
          fill="#60a5fa"
          fillOpacity={0.35}
          dot
        />
        <Tooltip
          contentStyle={{
            backgroundColor: "#0f172a",
            border: "1px solid #334155",
            borderRadius: 6,
            fontSize: 12,
          }}
          labelStyle={{ color: "#cbd5e1" }}
          formatter={(value: number) => [value.toFixed(2), "nota (1-5)"]}
        />
      </RadarChart>
    </ResponsiveContainer>
  );
}
