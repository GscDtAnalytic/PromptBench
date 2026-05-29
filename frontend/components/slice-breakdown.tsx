"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  LabelList,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { SliceLabel, SliceMetrics } from "@/lib/types";
import { SLICE_FILL, SLICE_LABEL_SHORT, SLICE_ORDER } from "@/lib/slice-style";

interface Props {
  perSlice: Record<string, SliceMetrics>;
  /** linha horizontal de "score mínimo aceitável" — opcional. */
  thresholdLine?: number;
}

export function SliceBreakdown({ perSlice, thresholdLine = 0.5 }: Props) {
  const data = SLICE_ORDER.filter((k) => perSlice[k]).map((k) => ({
    slice: k,
    label: SLICE_LABEL_SHORT[k as SliceLabel],
    score: perSlice[k].aggregate_score,
    fill: SLICE_FILL[k as SliceLabel],
  }));
  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={data} margin={{ top: 16, right: 8, left: -8, bottom: 0 }}>
        <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" vertical={false} />
        <XAxis
          dataKey="label"
          tick={{ fill: "#94a3b8", fontSize: 11 }}
          tickLine={false}
          axisLine={{ stroke: "#334155" }}
        />
        <YAxis
          domain={[0, 1]}
          ticks={[0, 0.25, 0.5, 0.75, 1]}
          tick={{ fill: "#64748b", fontSize: 10 }}
          tickLine={false}
          axisLine={{ stroke: "#334155" }}
        />
        <ReferenceLine
          y={thresholdLine}
          stroke="#475569"
          strokeDasharray="4 4"
          label={{
            value: `mín ${thresholdLine}`,
            position: "insideTopRight",
            fill: "#64748b",
            fontSize: 10,
          }}
        />
        <Tooltip
          cursor={{ fill: "rgba(148,163,184,0.06)" }}
          contentStyle={{
            backgroundColor: "#0f172a",
            border: "1px solid #334155",
            borderRadius: 6,
            fontSize: 12,
          }}
          labelStyle={{ color: "#cbd5e1" }}
          formatter={(value: number) => [value.toFixed(3), "score"]}
        />
        <Bar dataKey="score" radius={[4, 4, 0, 0]}>
          {data.map((d) => (
            <Cell key={d.slice} fill={d.fill} />
          ))}
          <LabelList
            dataKey="score"
            position="top"
            formatter={(v: number) => v.toFixed(2)}
            style={{ fill: "#cbd5e1", fontSize: 10 }}
          />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
