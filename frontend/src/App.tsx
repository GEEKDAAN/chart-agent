import { FormEvent, useState } from "react";

import { ChartPanel } from "./components/ChartPanel";
import { sendChartMessage } from "./lib/api";
import { applyChartAction } from "./lib/chartSpec";
import type { ChartSpec } from "./types/chart";

const QUICK_PROMPTS = [
  "看最近30天各渠道销售额",
  "把抖音改成红色",
  "加一列利润率",
  "换成折线图",
  "解释一下这个图"
];

export function App() {
  const [chart, setChart] = useState<ChartSpec | null>(null);
  const [message, setMessage] = useState(QUICK_PROMPTS[0]);
  const [status, setStatus] = useState("后端运行后，可以发送自然语言生成图表。");
  const [loading, setLoading] = useState(false);

  async function submit(nextMessage = message) {
    const trimmed = nextMessage.trim();
    if (!trimmed) return;
    setLoading(true);
    setStatus("处理中...");
    try {
      const response = await sendChartMessage(trimmed, chart);
      const nextChart = applyChartAction(chart, response.action);
      setChart(nextChart);
      setStatus(response.action.message);
      setMessage(trimmed);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "请求失败");
    } finally {
      setLoading(false);
    }
  }

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void submit();
  }

  return (
    <main className="app-shell">
      <section className="workspace">
        <header className="topbar">
          <div>
            <h1>chart-agent</h1>
            <p>基于受控 ChartSpec 协议的对话式图表生成 MVP</p>
          </div>
          <span className="status-pill">v0.2.0</span>
        </header>

        <ChartPanel chart={chart} />
      </section>

      <aside className="chat-panel">
        <div>
          <h2>对话输入</h2>
          <p>{status}</p>
        </div>

        <div className="prompt-list">
          {QUICK_PROMPTS.map((prompt) => (
            <button key={prompt} type="button" onClick={() => void submit(prompt)} disabled={loading}>
              {prompt}
            </button>
          ))}
        </div>

        <form onSubmit={onSubmit} className="message-form">
          <textarea value={message} onChange={(event) => setMessage(event.target.value)} rows={5} />
          <button type="submit" disabled={loading}>
            {loading ? "处理中" : "发送"}
          </button>
        </form>
      </aside>
    </main>
  );
}
