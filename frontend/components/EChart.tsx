"use client";

import * as echarts from "echarts";
import { useEffect, useRef } from "react";

function useIsDark() {
  if (typeof window === "undefined") return true;
  return document.documentElement.classList.contains("dark");
}

export default function EChart({
  option,
  height = 300,
}: {
  option: echarts.EChartsOption;
  height?: number;
}) {
  const ref = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<echarts.ECharts | null>(null);

  const isDark = useIsDark();

  useEffect(() => {
    if (!ref.current) return;
    if (chartRef.current) {
      chartRef.current.dispose();
    }
    const chart = echarts.init(ref.current, isDark ? "dark" : undefined, { renderer: "canvas" });
    chartRef.current = chart;
    chart.setOption(option);

    const ro = new ResizeObserver(() => chart.resize());
    ro.observe(ref.current);
    return () => {
      ro.disconnect();
      chart.dispose();
      chartRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isDark]);

  useEffect(() => {
    chartRef.current?.setOption(option, true);
  }, [option]);

  return <div ref={ref} style={{ width: "100%", height }} />;
}
