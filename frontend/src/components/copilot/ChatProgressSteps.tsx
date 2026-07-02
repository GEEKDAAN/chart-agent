import { useChartAgentProgress } from "../../lib/chartAgentProgressStore";
import type { ProgressStep } from "../../types/progress";

export function ChatProgressSteps({
  progressId,
  status,
  steps
}: {
  progressId: string | undefined;
  status: string;
  steps: ProgressStep[];
}) {
  const streamedSnapshot = useChartAgentProgress(progressId);
  const visibleSteps = streamedSnapshot?.steps ?? steps;
  const label = status === "complete" ? "已完成" : "执行中";

  return (
    <section className="chat-progress" aria-label="执行步骤">
      <div className="chat-progress-header">
        <h3>执行步骤</h3>
        <span>{label}</span>
      </div>
      <ol className="chat-progress-list">
        {visibleSteps.map((step, index) => (
          <li className={`chat-progress-step chat-progress-step-${step.status}`} key={step.id}>
            <span className="chat-progress-index">{step.status === "completed" ? "✓" : index + 1}</span>
            <div>
              <strong>{step.title}</strong>
              <p>{step.detail}</p>
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}
