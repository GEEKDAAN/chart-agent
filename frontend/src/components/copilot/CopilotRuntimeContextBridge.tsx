import { useEffect } from "react";
import { useAgentContext, useConfigureSuggestions } from "@copilotkit/react-core/v2";

import { copilotRuntimeUrl } from "../../lib/config";
import {
  installCopilotRuntimeContextPatch,
  syncChartAgentRuntimeContext,
  type ChartAgentRuntimeContext
} from "../../lib/copilotRuntimeContext";
import type { ChartSpec } from "../../types/chart";
import { toJsonSerializable } from "./utils";

const suggestions = [
  { title: "生成图表", message: "看最近30天各渠道销售额" },
  { title: "修改样式", message: "把抖音改成红色" },
  { title: "新增指标", message: "加一列利润率" },
  { title: "切换类型", message: "换成折线图" }
];

export function CopilotRuntimeContextBridge({ context }: { context: ChartAgentRuntimeContext }) {
  useEffect(() => {
    syncChartAgentRuntimeContext(context);
    installCopilotRuntimeContextPatch(copilotRuntimeUrl);
  }, [context]);

  useAgentContext({
    description: "chart-agent 当前图表上下文",
    value: toJsonSerializable(context)
  });

  useAgentContext({
    description: "chart-agent 前端指令",
    value: buildInstructions(context.currentChart)
  });

  useConfigureSuggestions(
    {
      suggestions
    },
    [context.currentChart]
  );

  return null;
}

function buildInstructions(chart: ChartSpec | null): string {
  const chartContext = chart
    ? JSON.stringify(
        {
          id: chart.id,
          title: chart.title,
          chartType: chart.chartType,
          columns: chart.data.columns,
          encoding: chart.encoding,
          style: chart.style
        },
        null,
        2
      )
    : "当前还没有图表。";

  return [
    "你是 chart-agent 的前端 CopilotKit 入口。",
    "只帮助用户表达图表生成或编辑需求。",
    "不要生成 React、SQL 或 ECharts option。",
    "后端只接受自然语言消息和当前 ChartSpec 上下文。",
    `当前图表上下文：${chartContext}`
  ].join("\n");
}
