import { useEffect, useRef } from "react";
import * as echarts from "echarts";

import { toEChartsOption, visibleRows } from "../lib/echartsOption";
import type { ChartSpec } from "../types/chart";

type ChartPanelProps = {
  chart: ChartSpec | null;
};

export function ChartPanel({ chart }: ChartPanelProps) {
  const ref = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!ref.current || !chart || chart.chartType === "table") return;
    const instance = echarts.init(ref.current);
    instance.setOption(toEChartsOption(chart), true);
    const resize = () => instance.resize();
    window.addEventListener("resize", resize);
    return () => {
      window.removeEventListener("resize", resize);
      instance.dispose();
    };
  }, [chart]);

  if (!chart) {
    return <div className="empty-state">通过 CopilotKit 侧边栏生成图表</div>;
  }

  if (chart.chartType === "table") {
    const visibleColumns = chart.style.visibleColumns ?? chart.data.columns.map((column) => column.key);
    const columns = chart.data.columns.filter((column) => visibleColumns.includes(column.key));
    return (
      <div className="table-wrap">
        <h2>{chart.title}</h2>
        <table>
          <thead>
            <tr>
              {columns.map((column) => (
                <th key={column.key}>{column.label}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {visibleRows(chart).map((row, rowIndex) => (
              <tr key={rowIndex}>
                {columns.map((column) => (
                  <td key={column.key}>{formatCell(row[column.key])}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  return <div ref={ref} className="chart-canvas" />;
}

function formatCell(value: unknown): string {
  if (typeof value === "number") return value.toLocaleString("zh-CN");
  return String(value ?? "");
}
