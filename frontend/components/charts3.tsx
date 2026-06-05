"use client";

import type { EChartsOption } from "echarts";
import EChart from "@/components/EChart";
import type { Revision } from "@/lib/api";

const AXIS = {
  axisLine: { lineStyle: { color: "rgba(128,140,158,0.3)" } },
  axisLabel: { color: "#5c6f86", fontSize: 10 },
  splitLine: { lineStyle: { color: "rgba(128,140,158,0.12)" } },
};

export function RevisionSeriesChart({ data }: { data: Revision }) {
  const series = data.forecast_series ?? [];
  const revs = data.revisions ?? [];
  const revByDate = new Map(revs.map((r) => [r.date, r.revision_mm]));

  const option: EChartsOption = {
    backgroundColor: "transparent",
    grid: { left: 52, right: 48, top: 28, bottom: 28 },
    tooltip: { trigger: "axis", backgroundColor: "#0f1620", borderColor: "#1e2a3a" },
    legend: { data: ["E[season] forecast", "Revision"], textStyle: { color: "#5c6f86" }, top: 0, right: 0 },
    xAxis: { type: "category", data: series.map((s) => s.date), ...AXIS },
    yAxis: [
      { type: "value", name: "mm", scale: true, nameTextStyle: { color: "#5c6f86" }, ...AXIS },
      { type: "value", name: "Δ", position: "right", nameTextStyle: { color: "#5c6f86" }, ...AXIS },
    ],
    series: [
      {
        name: "Revision", type: "bar", yAxisIndex: 1,
        data: series.map((s) => {
          const v = revByDate.get(s.date) ?? 0;
          return { value: v, itemStyle: { color: v >= 0 ? "#22c55e" : "#ef4444" } };
        }),
      },
      {
        name: "E[season] forecast", type: "line", smooth: true, showSymbol: true, symbolSize: 4,
        data: series.map((s) => s.expected_season_mm),
        lineStyle: { color: "#38bdf8", width: 2.5 },
      },
    ],
  };
  return <EChart option={option} height={320} />;
}
