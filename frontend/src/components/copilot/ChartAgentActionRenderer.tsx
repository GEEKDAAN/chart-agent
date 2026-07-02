import { useEffect, useRef } from "react";
import { useRenderTool } from "@copilotkit/react-core/v2";

import {
  ACTION_CREATE_CHART,
  ACTION_ERROR,
  ACTION_UPDATE_CHART,
  CHART_AGENT_ACTION_TOOL
} from "../../domain/chartAgentProtocol";
import { useLatestChartAgentAction } from "../../lib/chartAgentActionStore";
import type { ChartAgentAction } from "../../types/chart";
import { actionParametersSchema } from "./schemas";
import { safeJsonParse } from "./utils";

export function ChartAgentActionRenderer({
  onApplyAction,
  onApplyError
}: {
  onApplyAction: (action: ChartAgentAction) => void;
  onApplyError: (error: unknown) => void;
}) {
  const appliedActionIds = useRef(new Set<string>());
  const streamedAction = useLatestChartAgentAction();

  useEffect(() => {
    if (!streamedAction || appliedActionIds.current.has(streamedAction.actionId)) return;

    try {
      onApplyAction(streamedAction.action);
      appliedActionIds.current.add(streamedAction.actionId);
    } catch (error) {
      onApplyError(error);
      appliedActionIds.current.add(streamedAction.actionId);
    }
  }, [streamedAction, onApplyAction, onApplyError]);

  useRenderTool({
    name: CHART_AGENT_ACTION_TOOL,
    parameters: actionParametersSchema,
    render: ({ parameters, result }) => {
      const payload = readActionPayload(result);
      const actionId = payload?.actionId ?? parameters.actionId;
      const action = payload?.action ?? null;
      return (
        <ChartAgentActionApplier
          action={action}
          actionId={actionId}
          appliedActionIds={appliedActionIds.current}
          onApplyAction={onApplyAction}
          onApplyError={onApplyError}
        />
      );
    }
  });

  return null;
}

function ChartAgentActionApplier({
  action,
  actionId,
  appliedActionIds,
  onApplyAction,
  onApplyError
}: {
  action: ChartAgentAction | null;
  actionId: string | undefined;
  appliedActionIds: Set<string>;
  onApplyAction: (action: ChartAgentAction) => void;
  onApplyError: (error: unknown) => void;
}) {
  useEffect(() => {
    if (!action || !actionId || appliedActionIds.has(actionId)) return;

    try {
      onApplyAction(action);
      appliedActionIds.add(actionId);
    } catch (error) {
      onApplyError(error);
      appliedActionIds.add(actionId);
    }
  }, [action, actionId, appliedActionIds, onApplyAction, onApplyError]);

  return null;
}

function readActionPayload(result: unknown): { actionId?: string; action: ChartAgentAction | null } | null {
  if (!result) return null;

  const parsed = typeof result === "string" ? safeJsonParse(result) : result;
  if (!parsed || typeof parsed !== "object") return null;

  const value = parsed as Record<string, unknown>;
  const action = value.action;
  return {
    actionId: typeof value.actionId === "string" ? value.actionId : undefined,
    action: isChartAgentAction(action) ? action : null
  };
}

function isChartAgentAction(value: unknown): value is ChartAgentAction {
  if (!value || typeof value !== "object") return false;

  const action = value as Record<string, unknown>;
  if (action.type === ACTION_CREATE_CHART) {
    return typeof action.message === "string" && Boolean(action.chart && typeof action.chart === "object");
  }
  if (action.type === ACTION_UPDATE_CHART) {
    return typeof action.message === "string" && typeof action.chartId === "string" && Boolean(action.patch && typeof action.patch === "object");
  }
  if (action.type === ACTION_ERROR) {
    return typeof action.message === "string" && typeof action.code === "string";
  }
  return false;
}
