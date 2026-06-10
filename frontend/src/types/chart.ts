export type ChartType = "bar" | "line" | "pie" | "table";
export type ColumnType = "string" | "number" | "date" | "currency" | "percent";
export type Intent =
  | "create_chart"
  | "update_style"
  | "update_data"
  | "change_chart_type"
  | "explain_chart"
  | "unknown";

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
      type: "create_chart";
      message: string;
      chart: ChartSpec;
    }
  | {
      type: "update_chart";
      message: string;
      chartId: string;
      patch: ChartPatch;
    }
  | {
      type: "error";
      message: string;
      code: string;
    };

export type ChartAgentResponse = {
  conversationId: string;
  intent: Intent;
  action: ChartAgentAction;
};
