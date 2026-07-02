import { useRenderTool } from "@copilotkit/react-core/v2";

import { CHART_AGENT_UI_BLOCKS_TOOL } from "../../domain/chartAgentProtocol";
import type { ChartAgentUiBlock } from "../../types/chart";
import { uiBlocksParametersSchema } from "./schemas";
import { ChatUiBlocks } from "./ui-blocks/ChatUiBlocks";
import { safeJsonParse } from "./utils";

export function ChartAgentUiBlocksRenderer() {
  useRenderTool({
    name: CHART_AGENT_UI_BLOCKS_TOOL,
    parameters: uiBlocksParametersSchema,
    render: ({ parameters, result }) => {
      const payload = readUiBlocksPayload(result);
      const blocks = payload?.blocks ?? parameters.blocks ?? [];
      const uiBlockId = payload?.uiBlockId ?? parameters.uiBlockId;
      return <ChatUiBlocks blocks={blocks} uiBlockId={uiBlockId} />;
    }
  });

  return null;
}

function readUiBlocksPayload(result: unknown): { uiBlockId?: string; blocks: ChartAgentUiBlock[] } | null {
  if (!result) return null;

  const parsed = typeof result === "string" ? safeJsonParse(result) : result;
  const validation = uiBlocksParametersSchema.safeParse(parsed);
  return validation.success ? (validation.data as { uiBlockId?: string; blocks: ChartAgentUiBlock[] }) : null;
}
