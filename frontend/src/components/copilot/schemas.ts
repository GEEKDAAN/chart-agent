import { z } from "zod";

import {
  CHART_AGENT_MUTATING_ACTION_TYPES,
  COLUMN_TYPES,
  UI_BLOCK_DATA_TABLE,
  UI_BLOCK_INSIGHT_CARD,
  UI_BLOCK_METRIC_SUMMARY,
  UI_BLOCK_SUGGESTED_ACTIONS
} from "../../domain/chartAgentProtocol";

const progressStepSchema = z.object({
  id: z.string(),
  title: z.string(),
  detail: z.string(),
  status: z.enum(["pending", "running", "completed", "failed"])
});

export const progressParametersSchema = z.object({
  progressId: z.string().optional(),
  steps: z.array(progressStepSchema)
});

export const actionParametersSchema = z.object({
  actionId: z.string().optional(),
  actionType: z.enum(CHART_AGENT_MUTATING_ACTION_TYPES).optional()
});

const uiBlockColumnSchema = z.object({
  key: z.string(),
  label: z.string(),
  type: z.enum(COLUMN_TYPES)
});

const metricSummaryBlockSchema = z.object({
  type: z.literal(UI_BLOCK_METRIC_SUMMARY),
  title: z.string().optional(),
  items: z.array(
    z.object({
      label: z.string(),
      value: z.string(),
      description: z.string().optional()
    })
  )
});

const insightCardBlockSchema = z.object({
  type: z.literal(UI_BLOCK_INSIGHT_CARD),
  title: z.string().optional(),
  content: z.string()
});

const suggestedActionsBlockSchema = z.object({
  type: z.literal(UI_BLOCK_SUGGESTED_ACTIONS),
  title: z.string().optional(),
  actions: z.array(
    z.object({
      label: z.string(),
      message: z.string()
    })
  )
});

const dataTableBlockSchema = z.object({
  type: z.literal(UI_BLOCK_DATA_TABLE),
  title: z.string().optional(),
  data: z.object({
    columns: z.array(uiBlockColumnSchema),
    rows: z.array(z.record(z.string(), z.unknown()))
  })
});

const uiBlockSchema = z.discriminatedUnion("type", [
  metricSummaryBlockSchema,
  insightCardBlockSchema,
  suggestedActionsBlockSchema,
  dataTableBlockSchema
]);

export const uiBlocksParametersSchema = z.object({
  uiBlockId: z.string().optional(),
  blocks: z.array(uiBlockSchema)
});
