import { useMemo } from "react";
import { CopilotKitProvider, CopilotSidebar } from "@copilotkit/react-core/v2";
import "@copilotkit/react-core/v2/styles.css";

import { CHART_AGENT_ID, DEFAULT_PAGE_CONTEXT, DEFAULT_USER_CONTEXT } from "../domain/chartAgentProtocol";
import { copilotRuntimeUrl, isCopilotEnabled } from "../lib/config";
import type { ChartAgentRuntimeContext } from "../lib/copilotRuntimeContext";
import type { ChartAgentAction, ChartSpec } from "../types/chart";
import { ChartAgentActionRenderer } from "./copilot/ChartAgentActionRenderer";
import { ChartAgentProgressRenderer } from "./copilot/ChartAgentProgressRenderer";
import { ChartAgentUiBlocksRenderer } from "./copilot/ChartAgentUiBlocksRenderer";
import { CopilotRuntimeContextBridge } from "./copilot/CopilotRuntimeContextBridge";

type CopilotKitPanelProps = {
  chart: ChartSpec | null;
  onApplyAction: (action: ChartAgentAction) => void;
  onApplyError: (error: unknown) => void;
};

export function CopilotKitPanel({ chart, onApplyAction, onApplyError }: CopilotKitPanelProps) {
  const runtimeContext = useMemo<ChartAgentRuntimeContext>(
    () => ({
      currentChart: chart,
      pageContext: DEFAULT_PAGE_CONTEXT,
      userContext: DEFAULT_USER_CONTEXT
    }),
    [chart]
  );

  if (!isCopilotEnabled) {
    return null;
  }

  return (
    <CopilotKitProvider
      runtimeUrl={copilotRuntimeUrl}
      properties={runtimeContext}
      showDevConsole={false}
      onError={({ error, code, context }) => {
        onApplyError(new Error(`CopilotKit 请求失败：${code} ${error.message} ${JSON.stringify(context)}`));
      }}
    >
      <CopilotRuntimeContextBridge context={runtimeContext} />
      <ChartAgentProgressRenderer />
      <ChartAgentUiBlocksRenderer />
      <ChartAgentActionRenderer onApplyAction={onApplyAction} onApplyError={onApplyError} />
      <CopilotSidebar
        agentId={CHART_AGENT_ID}
        defaultOpen
        width={420}
        labels={{
          modalHeaderTitle: "chart-agent",
          welcomeMessageText: "描述你想生成或修改的图表。",
          chatInputPlaceholder: "输入图表需求..."
        }}
      />
    </CopilotKitProvider>
  );
}
