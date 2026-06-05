"use client";

import type { EChartsOption } from "echarts";
import EChart from "@/components/EChart";
import type { ImpactRow, MJOPanel, Scenario } from "@/lib/api";

const AXIS = {
  axisLine: { lineStyle: { color: "rgba(128,140,158,0.3)" } },
  axisLabel: { color: "#5c6f86", fontSize: 10 },
  splitLine: { lineStyle: { color: "rgba(128,140,158,0.12)" } },
};

export function ImpactBars({ impact, normal }: { impact: ImpactRow[]; normal: number }) {
  const option: EChartsOption = {
    backgroundColor: "transparent",
    grid: { left: 44, right: 12, top: 16, bottom: 24 },
    tooltip: { trigger: "axis", backgroundColor: "#0f1620", borderColor: "#1e2a3a" },
    xAxis: { type: "category", data: impact.map((i) => `${i.state} (${i.n_years})`), ...AXIS },
    yAxis: { type: "value", name: "mm", scale: true, nameTextStyle: { color: "#5c6f86" }, ...AXIS },
    series: [
      {
        type: "bar",
        data: impact.map((i) => ({
          value: Math.round(i.mean_season_mm),
          itemStyle: { color: (i.deviation_pct ?? 0) >= 0 ? "#22c55e" : "#ef4444" },
        })),
        markLine: {
          symbol: "none",
          data: [{ yAxis: Math.round(normal), label: { formatter: "normal", color: "#5c6f86", fontSize: 9 }, lineStyle: { color: "#5c6f86", type: "dashed" } }],
        },
      },
    ],
  };
  return <EChart option={option} height={200} />;
}

export function MJOPhaseChart({ mjo }: { mjo: MJOPanel }) {
  const data = mjo.phase_rainfall;
  const option: EChartsOption = {
    backgroundColor: "transparent",
    grid: { left: 44, right: 12, top: 16, bottom: 28 },
    tooltip: { trigger: "axis", backgroundColor: "#0f1620", borderColor: "#1e2a3a" },
    xAxis: { type: "category", data: data.map((p) => `P${p.phase}`), name: "MJO phase", nameLocation: "middle", nameGap: 22, nameTextStyle: { color: "#5c6f86" }, ...AXIS },
    yAxis: { type: "value", name: "mm/day", nameTextStyle: { color: "#5c6f86" }, ...AXIS },
    series: [
      {
        type: "bar",
        data: data.map((p) => ({
          value: p.mean_daily_mm,
          itemStyle: { color: [1, 2, 3, 4].includes(p.phase) ? "#38bdf8" : "#5c6f86" },
        })),
        markLine: {
          symbol: "none",
          data: [{ yAxis: mjo.baseline_daily_mm, label: { formatter: "avg", color: "#5c6f86", fontSize: 9 }, lineStyle: { color: "#5c6f86", type: "dashed" } }],
        },
      },
    ],
  };
  return <EChart option={option} height={220} />;
}

export function ScenarioChart({ scenarios, normal }: { scenarios: Scenario[]; normal: number }) {
  const option: EChartsOption = {
    backgroundColor: "transparent",
    grid: { left: 56, right: 16, top: 16, bottom: 70 },
    tooltip: { trigger: "axis", backgroundColor: "#0f1620", borderColor: "#1e2a3a" },
    xAxis: { type: "category", data: scenarios.map((s) => s.label), axisLabel: { ...AXIS.axisLabel, rotate: 30, interval: 0, width: 90, overflow: "truncate" }, axisLine: AXIS.axisLine },
    yAxis: { type: "value", name: "season mm", scale: true, nameTextStyle: { color: "#5c6f86" }, ...AXIS },
    series: [
      {
        type: "bar",
        data: scenarios.map((s) => ({
          value: s.projected_season_mm,
          itemStyle: { color: (s.deviation_pct ?? 0) >= 0 ? "#22c55e" : "#ef4444" },
        })),
        markLine: {
          symbol: "none",
          data: [{ yAxis: Math.round(normal), label: { formatter: "normal", color: "#5c6f86", fontSize: 9 }, lineStyle: { color: "#5c6f86", type: "dashed" } }],
        },
      },
    ],
  };
  return <EChart option={option} height={300} />;
}
