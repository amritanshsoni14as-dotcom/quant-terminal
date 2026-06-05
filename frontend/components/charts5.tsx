"use client";

import type { EChartsOption } from "echarts";
import EChart from "@/components/EChart";
import type { Research } from "@/lib/api";

const AXIS = {
  axisLine: { lineStyle: { color: "rgba(128,140,158,0.3)" } },
  axisLabel: { color: "#64748b", fontSize: 10 },
  splitLine: { lineStyle: { color: "rgba(128,140,158,0.12)" } },
};
const TT = { backgroundColor: "#0f1620", borderColor: "rgba(128,140,158,0.3)" };

export function CorrHeatmap({ data }: { data: NonNullable<Research["correlation"]> }) {
  const { labels, matrix } = data;
  const cells: [number, number, number][] = [];
  for (let i = 0; i < labels.length; i++)
    for (let j = 0; j < labels.length; j++) cells.push([j, i, matrix[i][j]]);

  const option: EChartsOption = {
    backgroundColor: "transparent",
    grid: { left: 70, right: 16, top: 16, bottom: 60 },
    tooltip: { position: "top", ...TT,
      formatter: (p: unknown) => {
        const v = (p as { value: number[] }).value;
        return `${labels[v[1]]} × ${labels[v[0]]}: ${v[2]}`;
      } },
    xAxis: { type: "category", data: labels, splitArea: { show: true }, axisLabel: { ...AXIS.axisLabel, rotate: 40 }, axisLine: AXIS.axisLine },
    yAxis: { type: "category", data: labels, splitArea: { show: true }, axisLabel: AXIS.axisLabel, axisLine: AXIS.axisLine },
    visualMap: {
      min: -1, max: 1, calculable: true, orient: "horizontal", left: "center", bottom: 0,
      inRange: { color: ["#ef4444", "#0f1620", "#22c55e"] },
      textStyle: { color: "#64748b" }, itemHeight: 80,
    },
    series: [{
      type: "heatmap", data: cells,
      label: { show: true, color: "#c5d4e3", fontSize: 9 },
      emphasis: { itemStyle: { shadowBlur: 6, shadowColor: "rgba(0,0,0,0.4)" } },
    }],
  };
  return <EChart option={option} height={360} />;
}

export function LeadLagChart({ data }: { data: NonNullable<Research["leadlag"]> }) {
  const lags = data[0]?.series.map((s) => s.lag) ?? [];
  const palette = ["#38bdf8", "#22c55e", "#f59e0b"];
  const option: EChartsOption = {
    backgroundColor: "transparent",
    grid: { left: 44, right: 16, top: 28, bottom: 40 },
    tooltip: { trigger: "axis", ...TT },
    legend: { data: data.map((d) => d.driver), textStyle: { color: "#64748b" }, top: 0 },
    xAxis: { type: "category", data: lags, name: "driver lead (months) →", nameLocation: "middle", nameGap: 26, nameTextStyle: { color: "#64748b" }, ...AXIS },
    yAxis: { type: "value", name: "corr", min: -0.6, max: 0.6, nameTextStyle: { color: "#64748b" }, ...AXIS },
    series: data.map((d, i) => ({
      name: d.driver, type: "line", smooth: true, showSymbol: false,
      data: d.series.map((s) => s.corr),
      lineStyle: { color: palette[i % palette.length], width: 2 },
      itemStyle: { color: palette[i % palette.length] },
    })),
  };
  return <EChart option={option} height={300} />;
}

export function SeasonalityChart({ data }: { data: NonNullable<Research["seasonality"]> }) {
  const MONTHS = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  const option: EChartsOption = {
    backgroundColor: "transparent",
    grid: { left: 48, right: 16, top: 16, bottom: 28 },
    tooltip: { trigger: "axis", ...TT },
    xAxis: { type: "category", data: data.map((d) => MONTHS[d.month]), ...AXIS },
    yAxis: { type: "value", name: "mm", nameTextStyle: { color: "#64748b" }, ...AXIS },
    series: [{
      type: "bar", data: data.map((d) => d.mean_mm),
      itemStyle: { color: "#3b82f6" },
    }],
  };
  return <EChart option={option} height={260} />;
}
