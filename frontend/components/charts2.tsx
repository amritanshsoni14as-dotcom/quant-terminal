"use client";

import type { EChartsOption } from "echarts";
import EChart from "@/components/EChart";
import type { FairValue, Probability } from "@/lib/api";

const AXIS = {
  axisLine: { lineStyle: { color: "rgba(128,140,158,0.3)" } },
  axisLabel: { color: "#5c6f86", fontSize: 10 },
  splitLine: { lineStyle: { color: "rgba(128,140,158,0.12)" } },
};

export function ProbabilityDistChart({ data }: { data: Probability }) {
  const curve = data.curve ?? [];
  const t = data.thresholds ?? {};
  const markLines = [
    { name: "normal", x: t.normal, color: "#5c6f86" },
    { name: "+10%", x: t.above_10, color: "#22c55e" },
    { name: "+20%", x: t.above_20, color: "#16a34a" },
    { name: "-10%", x: t.below_10, color: "#ef4444" },
    { name: "-20%", x: t.below_20, color: "#b91c1c" },
    { name: "E[season]", x: data.expected_mm, color: "#38bdf8" },
  ].filter((m) => m.x != null);

  const option: EChartsOption = {
    backgroundColor: "transparent",
    grid: { left: 16, right: 16, top: 24, bottom: 36 },
    tooltip: { trigger: "axis", backgroundColor: "#0f1620", borderColor: "#1e2a3a" },
    xAxis: { type: "category", data: curve.map((p) => p.x), name: "Seasonal rainfall (mm)", nameLocation: "middle", nameGap: 26, nameTextStyle: { color: "#5c6f86" }, ...AXIS, axisLabel: { ...AXIS.axisLabel, interval: 9 } },
    yAxis: { type: "value", show: false, ...AXIS },
    series: [
      {
        type: "line", smooth: true, showSymbol: false,
        data: curve.map((p) => p.pdf),
        lineStyle: { color: "#38bdf8", width: 2 },
        areaStyle: { color: "rgba(56,189,248,0.12)" },
        markLine: {
          symbol: "none",
          data: markLines.map((m) => ({
            xAxis: curve.findIndex((p) => p.x >= (m.x as number)),
            label: { formatter: m.name, color: m.color, fontSize: 9 },
            lineStyle: { color: m.color, type: m.name === "E[season]" ? "solid" : "dashed", width: m.name === "E[season]" ? 2 : 1 },
          })),
        },
      },
    ],
  };
  return <EChart option={option} height={300} />;
}

export function PayoffCurveChart({ data }: { data: FairValue }) {
  const curve = data.payoff_curve ?? [];
  const option: EChartsOption = {
    backgroundColor: "transparent",
    grid: { left: 56, right: 16, top: 20, bottom: 36 },
    tooltip: { trigger: "axis", backgroundColor: "#0f1620", borderColor: "#1e2a3a" },
    xAxis: { type: "category", data: curve.map((p) => p.index), name: "rainfall index (mm)", nameLocation: "middle", nameGap: 26, nameTextStyle: { color: "#5c6f86" }, ...AXIS, axisLabel: { ...AXIS.axisLabel, interval: 9 } },
    yAxis: { type: "value", name: "payoff", nameTextStyle: { color: "#5c6f86" }, ...AXIS },
    series: [
      {
        type: "line", smooth: false, showSymbol: false,
        data: curve.map((p) => p.payoff),
        lineStyle: { color: "#f59e0b", width: 2 },
        markLine: data.expected_settle != null ? {
          symbol: "none",
          data: [{ xAxis: curve.findIndex((p) => p.index >= (data.expected_settle as number)), label: { formatter: "E[settle]", color: "#38bdf8", fontSize: 9 }, lineStyle: { color: "#38bdf8", width: 2 } }],
        } : undefined,
      },
    ],
  };
  return <EChart option={option} height={300} />;
}
