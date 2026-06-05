"use client";

import type { EChartsOption } from "echarts";
import EChart from "@/components/EChart";
import type { CumPoint, DailyPoint, MonthlyPoint, WeeklyPoint } from "@/lib/api";

const AXIS = {
  axisLine: { lineStyle: { color: "rgba(128,140,158,0.3)" } },
  axisLabel: { color: "#5c6f86", fontSize: 10 },
  splitLine: { lineStyle: { color: "rgba(128,140,158,0.12)" } },
};
const base = (opt: EChartsOption): EChartsOption => ({
  backgroundColor: "transparent",
  grid: { left: 48, right: 16, top: 16, bottom: 28 },
  tooltip: { trigger: "axis", backgroundColor: "#0f1620", borderColor: "#1e2a3a" },
  ...opt,
});

export function DailyRainChart({ data }: { data: DailyPoint[] }) {
  const option = base({
    legend: { data: ["Daily", "7d sum", "30d sum"], textStyle: { color: "#5c6f86" }, top: 0, right: 0 },
    grid: { left: 48, right: 16, top: 28, bottom: 28 },
    xAxis: { type: "category", data: data.map((d) => d.date), ...AXIS },
    yAxis: { type: "value", name: "mm", nameTextStyle: { color: "#5c6f86" }, ...AXIS },
    series: [
      { name: "Daily", type: "bar", data: data.map((d) => d.rainfall_mm), itemStyle: { color: "#3b82f6" } },
      { name: "7d sum", type: "line", smooth: true, showSymbol: false, data: data.map((d) => d.roll7), lineStyle: { color: "#38bdf8", width: 1.5 } },
      { name: "30d sum", type: "line", smooth: true, showSymbol: false, data: data.map((d) => d.roll30), lineStyle: { color: "#f59e0b", width: 1.5 } },
    ],
  });
  return <EChart option={option} height={320} />;
}

export function WeeklyChart({ data }: { data: WeeklyPoint[] }) {
  const option = base({
    xAxis: { type: "category", data: data.map((d) => d.week), ...AXIS },
    yAxis: { type: "value", name: "mm", nameTextStyle: { color: "#5c6f86" }, ...AXIS },
    series: [{ type: "bar", data: data.map((d) => d.rainfall_mm), itemStyle: { color: "#38bdf8" } }],
  });
  return <EChart option={option} height={280} />;
}

export function MonthlyChart({ data }: { data: MonthlyPoint[] }) {
  const option = base({
    xAxis: { type: "category", data: data.map((d) => d.month), ...AXIS },
    yAxis: { type: "value", name: "mm", nameTextStyle: { color: "#5c6f86" }, ...AXIS },
    series: [
      {
        type: "bar",
        data: data.map((d) => d.rainfall_mm),
        itemStyle: { color: "#3b82f6" },
      },
    ],
  });
  return <EChart option={option} height={280} />;
}

export function CumulativeChart({ data }: { data: CumPoint[] }) {
  const option = base({
    legend: { data: ["Actual", "Climatology", "P10–P90"], textStyle: { color: "#5c6f86" }, top: 0, right: 0 },
    grid: { left: 56, right: 16, top: 28, bottom: 28 },
    xAxis: { type: "category", data: data.map((d) => d.date), ...AXIS },
    yAxis: { type: "value", name: "cum mm", nameTextStyle: { color: "#5c6f86" }, ...AXIS },
    series: [
      // P10..P90 band rendered as stacked transparent + filled area.
      { name: "P10–P90", type: "line", stack: "band", showSymbol: false, lineStyle: { opacity: 0 }, data: data.map((d) => d.p10) },
      { name: "P10–P90", type: "line", stack: "band", showSymbol: false, lineStyle: { opacity: 0 }, areaStyle: { color: "rgba(56,189,248,0.12)" }, data: data.map((d) => +(d.p90 - d.p10).toFixed(1)) },
      { name: "Climatology", type: "line", smooth: true, showSymbol: false, data: data.map((d) => d.climatology), lineStyle: { color: "#5c6f86", type: "dashed" } },
      { name: "Actual", type: "line", smooth: true, showSymbol: false, data: data.map((d) => d.actual), lineStyle: { color: "#22c55e", width: 2.5 } },
    ],
  });
  return <EChart option={option} height={320} />;
}
