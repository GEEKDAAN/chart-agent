import type { EChartsOption } from "echarts";

import type { ChartSpec } from "../types/chart";

export function toEChartsOption(chart: ChartSpec): EChartsOption {
  if (chart.chartType === "table") {
    return {};
  }

  if (chart.chartType === "pie") {
    const category = chart.encoding.category;
    const value = chart.encoding.value;
    const rows = chart.data.rows;
    return {
      title: { text: chart.title, left: "center" },
      tooltip: { show: chart.style.showTooltip ?? true, trigger: "item" },
      legend: { show: chart.style.showLegend ?? true, bottom: 0 },
      series: [
        {
          type: "pie",
          radius: ["35%", "65%"],
          data: rows.map((row) => ({
            name: String(row[category ?? ""]),
            value: Number(row[value ?? ""] ?? 0),
            itemStyle: colorFor(chart, String(row[category ?? ""]))
          }))
        }
      ]
    };
  }

  const x = chart.encoding.x;
  const y = chart.encoding.y;
  const rows = chart.data.rows;
  const categories = rows.map((row) => String(row[x ?? ""]));

  return {
    title: { text: chart.title },
    tooltip: { show: chart.style.showTooltip ?? true, trigger: "axis" },
    legend: { show: chart.style.showLegend ?? true },
    grid: { left: 48, right: 24, top: 56, bottom: 42 },
    xAxis: { type: "category", data: categories },
    yAxis: { type: "value" },
    series: [
      {
        type: chart.chartType,
        smooth: chart.chartType === "line" ? chart.style.smooth ?? false : undefined,
        data: rows.map((row) => ({
          value: Number(row[y ?? ""] ?? 0),
          itemStyle: colorFor(chart, String(row[x ?? ""]))
        }))
      }
    ]
  };
}

function colorFor(chart: ChartSpec, key: string): { color?: string } | undefined {
  const color = chart.style.colors?.[key] ?? chart.style.colors?.default;
  return color ? { color } : undefined;
}
