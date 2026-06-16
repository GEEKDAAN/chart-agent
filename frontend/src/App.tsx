import { Suspense, lazy, useCallback, useState } from "react";

import { ChartPanel } from "./components/ChartPanel";
import { applyChartAction } from "./lib/chartSpec";
import { isCopilotEnabled } from "./lib/config";
import type { ChartAgentAction, ChartSpec } from "./types/chart";

const CopilotKitPanel = lazy(() =>
  import("./components/CopilotKitPanel").then((module) => ({ default: module.CopilotKitPanel }))
);

export function App() {
  const [chart, setChart] = useState<ChartSpec | null>(null);
  const [status, setStatus] = useState(
    isCopilotEnabled ? "等待 CopilotKit 指令" : "请配置 CopilotKit Runtime"
  );

  const applyAgentAction = useCallback(
    (action: ChartAgentAction) => {
      const nextChart = applyChartAction(chart, action);
      setChart(nextChart);
      setStatus(action.message);
    },
    [chart]
  );

  const handleApplyError = useCallback((error: unknown) => {
    const message = error instanceof Error ? error.message : "CopilotKit 图表应用失败";
    setStatus(message);
  }, []);

  return (
    <main className="app-shell">
      <section className="workspace">
        <header className="topbar">
          <div>
            <h1>chart-agent</h1>
            <p>{status}</p>
          </div>
          <div className="topbar-badges">
            <span className="status-pill">v0.11.4</span>
            <span className="status-pill">{isCopilotEnabled ? "CopilotKit 已启用" : "CopilotKit 未配置"}</span>
          </div>
        </header>

        <ChartPanel chart={chart} />
      </section>

      {isCopilotEnabled ? (
        <Suspense fallback={null}>
          <CopilotKitPanel
            chart={chart}
            onApplyAction={applyAgentAction}
            onApplyError={handleApplyError}
          />
        </Suspense>
      ) : null}
    </main>
  );
}
