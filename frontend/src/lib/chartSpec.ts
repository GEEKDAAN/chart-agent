import type { ChartAgentAction, ChartPatch, ChartSpec } from "../types/chart";

const SUPPORTED_TYPES = new Set(["bar", "line", "pie", "table"]);
const COLOR_PATTERN = /^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$/;

export function validateChartSpec(chart: ChartSpec): string[] {
  const errors: string[] = [];
  if (!chart.id) errors.push("图表缺少 id。");
  if (!chart.title) errors.push("图表缺少标题。");
  if (!SUPPORTED_TYPES.has(chart.chartType)) errors.push(`不支持的图表类型：${chart.chartType}`);
  if (!chart.data?.columns?.length) errors.push("图表缺少 columns。");
  if (!Array.isArray(chart.data?.rows)) errors.push("图表 rows 必须是数组。");

  const columnKeys = new Set(chart.data?.columns?.map((column) => column.key) ?? []);
  const referenced = [
    chart.encoding?.x,
    chart.encoding?.y,
    chart.encoding?.series,
    chart.encoding?.category,
    chart.encoding?.value
  ].filter(Boolean) as string[];
  for (const key of referenced) {
    if (!columnKeys.has(key)) errors.push(`encoding 引用了不存在的字段：${key}`);
  }

  if ((chart.chartType === "bar" || chart.chartType === "line") && (!chart.encoding.x || !chart.encoding.y)) {
    errors.push("柱状图和折线图必须配置 encoding.x 和 encoding.y。");
  }
  if (chart.chartType === "pie" && (!chart.encoding.category || !chart.encoding.value)) {
    errors.push("饼图必须配置 encoding.category 和 encoding.value。");
  }

  for (const [key, value] of Object.entries(chart.style.colors ?? {})) {
    if (!COLOR_PATTERN.test(value)) errors.push(`${key} 的颜色值不合法：${value}`);
  }

  for (const key of chart.style.visibleColumns ?? []) {
    if (!columnKeys.has(key)) errors.push(`visibleColumns 引用了不存在的字段：${key}`);
  }
  return errors;
}

export function mergeChartPatch(current: ChartSpec, patch: ChartPatch): ChartSpec {
  return {
    ...current,
    title: patch.title ?? current.title,
    chartType: patch.chartType ?? current.chartType,
    data: patch.data ?? current.data,
    encoding: patch.encoding ? { ...current.encoding, ...patch.encoding } : current.encoding,
    style: patch.style ? { ...current.style, ...patch.style } : current.style
  };
}

export function applyChartAction(current: ChartSpec | null, action: ChartAgentAction): ChartSpec {
  if (action.type === "error") {
    throw new Error(action.message);
  }
  if (action.type === "create_chart") {
    assertValid(action.chart);
    return action.chart;
  }
  if (!current) {
    throw new Error("当前没有可更新的图表。");
  }
  if (current.id !== action.chartId) {
    throw new Error("后端返回的 chartId 与当前图表不一致。");
  }
  const next = mergeChartPatch(current, action.patch);
  assertValid(next);
  return next;
}

function assertValid(chart: ChartSpec): void {
  const errors = validateChartSpec(chart);
  if (errors.length) {
    throw new Error(errors.join("\n"));
  }
}
