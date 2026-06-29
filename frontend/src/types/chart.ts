import type {
  ACTION_CREATE_CHART,
  ACTION_ERROR,
  ACTION_UPDATE_CHART,
  CHART_AGENT_ACTION_TYPES,
  CHART_AGENT_UI_BLOCK_TYPES,
  CHART_TYPES,
  COLUMN_TYPES,
  INTENTS,
  UI_BLOCK_DATA_TABLE,
  UI_BLOCK_INSIGHT_CARD,
  UI_BLOCK_METRIC_SUMMARY,
  UI_BLOCK_SUGGESTED_ACTIONS
} from "../domain/chartAgentProtocol";

export type ChartType = (typeof CHART_TYPES)[number];
export type ColumnType = (typeof COLUMN_TYPES)[number];
export type Intent = (typeof INTENTS)[number];
export type ChartAgentActionType = (typeof CHART_AGENT_ACTION_TYPES)[number];
export type ChartAgentUiBlockType = (typeof CHART_AGENT_UI_BLOCK_TYPES)[number];

export type ChartColumn = {
  key: string;
  label: string;
  type: ColumnType;
};

export type ChartData = {
  columns: ChartColumn[];
  rows: Record<string, unknown>[];
};

export type ChartEncoding = {
  x?: string;
  y?: string;
  series?: string;
  category?: string;
  value?: string;
};

export type ChartStyle = {
  visibleColumns?: string[];
  colors?: Record<string, string>;
  hiddenValues?: Record<string, string[]>;
  showLegend?: boolean;
  showTooltip?: boolean;
  stacked?: boolean;
  smooth?: boolean;
  columnStyles?: Record<
    string,
    {
      color?: string;
      backgroundColor?: string;
      width?: number;
    }
  >;
};

export type ChartSpec = {
  id: string;
  title: string;
  chartType: ChartType;
  data: ChartData;
  encoding: ChartEncoding;
  style: ChartStyle;
};

export type ChartPatch = {
  title?: string;
  chartType?: ChartType;
  data?: ChartData;
  encoding?: ChartEncoding;
  style?: ChartStyle;
};

export type ChartAgentAction =
  | {
      type: typeof ACTION_CREATE_CHART;
      message: string;
      chart: ChartSpec;
    }
  | {
      type: typeof ACTION_UPDATE_CHART;
      message: string;
      chartId: string;
      patch: ChartPatch;
    }
  | {
      type: typeof ACTION_ERROR;
      message: string;
      code: string;
    };

export type MetricSummaryItem = {
  label: string;
  value: string;
  description?: string;
};

export type SuggestedAction = {
  label: string;
  message: string;
};

export type DataTableBlockData = {
  columns: ChartColumn[];
  rows: Record<string, unknown>[];
};

export type ChartAgentUiBlock =
  | {
      type: typeof UI_BLOCK_METRIC_SUMMARY;
      title?: string;
      items: MetricSummaryItem[];
    }
  | {
      type: typeof UI_BLOCK_INSIGHT_CARD;
      title?: string;
      content: string;
    }
  | {
      type: typeof UI_BLOCK_SUGGESTED_ACTIONS;
      title?: string;
      actions: SuggestedAction[];
    }
  | {
      type: typeof UI_BLOCK_DATA_TABLE;
      title?: string;
      data: DataTableBlockData;
    };

export type ChartAgentResponse = {
  conversationId: string;
  intent: Intent;
  action: ChartAgentAction;
  uiBlocks?: ChartAgentUiBlock[];
};
