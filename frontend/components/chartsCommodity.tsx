"use client";

import type { EChartsOption } from "echarts";
import EChart from "@/components/EChart";
import type { CommodityTechnicals, PricePoint } from "@/lib/api";

const AXIS = {
  axisLine: { lineStyle: { color: "rgba(128,140,158,0.3)" } },
  axisLabel: { color: "#64748b", fontSize: 10 },
  splitLine: { lineStyle: { color: "rgba(128,140,158,0.12)" } },
};
const TT = { backgroundColor: "#0f1620", borderColor: "rgba(128,140,158,0.3)" };

export function PriceCandles({ data }: { data: PricePoint[] }) {
  const labels = data.map((d) => d.date);
  // ECharts candlestick expects [open, close, low, high]
  const ohlc = data.map((d) => [d.open, d.close, d.low, d.high]);
  const option: EChartsOption = {
    backgroundColor: "transparent",
    grid: { left: 56, right: 16, top: 28, bottom: 50 },
    tooltip: { trigger: "axis", ...TT },
    legend: { data: ["Price", "SMA50", "SMA200"], textStyle: { color: "#64748b" }, top: 0, right: 0 },
    xAxis: { type: "category", data: labels, ...AXIS, axisLabel: { ...AXIS.axisLabel, interval: Math.floor(labels.length / 8) } },
    yAxis: { type: "value", scale: true, ...AXIS },
    dataZoom: [{ type: "inside" }, { type: "slider", height: 16, bottom: 16, borderColor: "rgba(128,140,158,0.3)", textStyle: { color: "#64748b" } }],
    series: [
      { name: "Price", type: "candlestick", data: ohlc,
        itemStyle: { color: "#22c55e", color0: "#ef4444", borderColor: "#22c55e", borderColor0: "#ef4444" } },
      { name: "SMA50", type: "line", smooth: true, showSymbol: false, data: data.map((d) => d.sma50), lineStyle: { color: "#38bdf8", width: 1.3 } },
      { name: "SMA200", type: "line", smooth: true, showSymbol: false, data: data.map((d) => d.sma200), lineStyle: { color: "#f59e0b", width: 1.3 } },
    ],
  };
  return <EChart option={option} height={360} />;
}

export function MacdChart({ data }: { data: NonNullable<CommodityTechnicals["macd_series"]> }) {
  const labels = data.map((d) => d.date);
  const option: EChartsOption = {
    backgroundColor: "transparent",
    grid: { left: 48, right: 16, top: 26, bottom: 28 },
    tooltip: { trigger: "axis", ...TT },
    legend: { data: ["MACD", "Signal", "Hist"], textStyle: { color: "#64748b" }, top: 0 },
    xAxis: { type: "category", data: labels, ...AXIS, axisLabel: { ...AXIS.axisLabel, interval: Math.floor(labels.length / 6) } },
    yAxis: { type: "value", ...AXIS },
    series: [
      { name: "Hist", type: "bar", data: data.map((d) => ({ value: d.hist, itemStyle: { color: d.hist >= 0 ? "#22c55e" : "#ef4444" } })) },
      { name: "MACD", type: "line", smooth: true, showSymbol: false, data: data.map((d) => d.macd), lineStyle: { color: "#38bdf8", width: 1.5 } },
      { name: "Signal", type: "line", smooth: true, showSymbol: false, data: data.map((d) => d.signal), lineStyle: { color: "#f59e0b", width: 1.5 } },
    ],
  };
  return <EChart option={option} height={220} />;
}
