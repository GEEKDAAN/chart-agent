import type {
  ACTION_CREATE_CHART,
  ACTION_ERROR,
  ACTION_UPDATE_CHART,
  CHART_AGENT_ACTION_TYPES,
  CHART_TYPES,
  COLUMN_TYPES,
  INTENTS
} from "../domain/chartAgentProtocol";

export type ChartType = (typeof CHART_TYPES)[number];
export type ColumnType = (typeof COLUMN_TYPES)[number];
export type Intent = (typeof INTENTS)[number];
export type ChartAgentActionType = (typeof CHART_AGENT_ACTION_TYPES)[number];

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

export type ChartAgentResponse = {
  conversationId: string;
  intent: Intent;
  action: ChartAgentAction;
};
