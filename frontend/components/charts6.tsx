"use client";

import type { EChartsOption } from "echarts";
import EChart from "@/components/EChart";
import type { Satellite } from "@/lib/api";

const AXIS = {
  axisLine: { lineStyle: { color: "rgba(128,140,158,0.3)" } },
  axisLabel: { color: "#64748b", fontSize: 10 },
  splitLine: { lineStyle: { color: "rgba(128,140,158,0.12)" } },
};

export function SatelliteHourlyChart({ data }: { data: NonNullable<Satellite["hourly"]> }) {
  const labels = data.map((d, i) => (i % 3 === 0 ? d.time : ""));
  const option: EChartsOption = {
    backgroundColor: "transparent",
    grid: { left: 40, right: 44, top: 28, bottom: 28 },
    tooltip: { trigger: "axis", backgroundColor: "#0f1620", borderColor: "rgba(128,140,158,0.3)" },
    legend: { data: ["Cloud cover", "Rain prob", "Precip"], textStyle: { color: "#64748b" }, top: 0 },
    xAxis: { type: "category", data: labels, ...AXIS },
    yAxis: [
      { type: "value", name: "%", max: 100, nameTextStyle: { color: "#64748b" }, ...AXIS },
      { type: "value", name: "mm", position: "right", nameTextStyle: { color: "#64748b" }, ...AXIS },
    ],
    series: [
      { name: "Cloud cover", type: "line", smooth: true, showSymbol: false, areaStyle: { color: "rgba(92,111,134,0.18)" },
        data: data.map((d) => d.cloud), lineStyle: { color: "#5c6f86", width: 1.5 } },
      { name: "Rain prob", type: "line", smooth: true, showSymbol: false,
        data: data.map((d) => d.rain_prob), lineStyle: { color: "#38bdf8", width: 2 } },
      { name: "Precip", type: "bar", yAxisIndex: 1,
        data: data.map((d) => d.precip), itemStyle: { color: "#3b82f6" } },
    ],
  };
  return <EChart option={option} height={260} />;
}
