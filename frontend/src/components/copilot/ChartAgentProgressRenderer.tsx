import { useRenderTool } from "@copilotkit/react-core/v2";

import { CHART_AGENT_PROGRESS_TOOL } from "../../domain/chartAgentProtocol";
import type { ProgressStep } from "../../types/progress";
import { ChatProgressSteps } from "./ChatProgressSteps";
import { progressParametersSchema } from "./schemas";
import { safeJsonParse } from "./utils";

export function ChartAgentProgressRenderer() {
  useRenderTool({
    name: CHART_AGENT_PROGRESS_TOOL,
    parameters: progressParametersSchema,
    render: ({ status, parameters, result }) => {
      const resultSteps = readProgressSteps(result);
      const resultProgressId = readProgressId(result);
      const progressId = resultProgressId ?? parameters.progressId;
      const steps = resultSteps.length > 0 ? resultSteps : parameters.steps ?? [];
      return <ChatProgressSteps progressId={progressId} status={status} steps={steps} />;
    }
  });

  return null;
}

function readProgressSteps(result: unknown): ProgressStep[] {
  if (!result) return [];

  const parsed = typeof result === "string" ? safeJsonParse(result) : result;
  const validation = progressParametersSchema.safeParse(parsed);
  return validation.success ? validation.data.steps : [];
}

function readProgressId(result: unknown): string | undefined {
  if (!result) return undefined;

  const parsed = typeof result === "string" ? safeJsonParse(result) : result;
  const validation = progressParametersSchema.safeParse(parsed);
  return validation.success ? validation.data.progressId : undefined;
}
