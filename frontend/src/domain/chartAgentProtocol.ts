export const APP_VERSION = "0.11.18";

export const CHART_AGENT_ID = "chart-agent";

export const CHART_AGENT_ACTION_TOOL = "chartAgentAction";
export const CHART_AGENT_PROGRESS_TOOL = "chartAgentProgress";

export const COPILOT_TOOL_CALL_ARGS_EVENT = "TOOL_CALL_ARGS";
export const COPILOT_TOOL_CALL_RESULT_EVENT = "TOOL_CALL_RESULT";

export const ACTION_CREATE_CHART = "create_chart";
export const ACTION_UPDATE_CHART = "update_chart";
export const ACTION_ERROR = "error";

export const CHART_AGENT_ACTION_TYPES = [
  ACTION_CREATE_CHART,
  ACTION_UPDATE_CHART,
  ACTION_ERROR
] as const;

export const CHART_AGENT_MUTATING_ACTION_TYPES = [
  ACTION_CREATE_CHART,
  ACTION_UPDATE_CHART
] as const;

export const CHART_TYPE_BAR = "bar";
export const CHART_TYPE_LINE = "line";
export const CHART_TYPE_PIE = "pie";
export const CHART_TYPE_TABLE = "table";

export const CHART_TYPES = [
  CHART_TYPE_BAR,
  CHART_TYPE_LINE,
  CHART_TYPE_PIE,
  CHART_TYPE_TABLE
] as const;

export const XY_CHART_TYPES = [CHART_TYPE_BAR, CHART_TYPE_LINE] as const;

export const COLUMN_TYPE_STRING = "string";
export const COLUMN_TYPE_NUMBER = "number";
export const COLUMN_TYPE_DATE = "date";
export const COLUMN_TYPE_CURRENCY = "currency";
export const COLUMN_TYPE_PERCENT = "percent";

export const COLUMN_TYPES = [
  COLUMN_TYPE_STRING,
  COLUMN_TYPE_NUMBER,
  COLUMN_TYPE_DATE,
  COLUMN_TYPE_CURRENCY,
  COLUMN_TYPE_PERCENT
] as const;

export const INTENT_CREATE_CHART = "create_chart";
export const INTENT_UPDATE_STYLE = "update_style";
export const INTENT_UPDATE_DATA = "update_data";
export const INTENT_CHANGE_CHART_TYPE = "change_chart_type";
export const INTENT_EXPLAIN_CHART = "explain_chart";
export const INTENT_UNKNOWN = "unknown";

export const INTENTS = [
  INTENT_CREATE_CHART,
  INTENT_UPDATE_STYLE,
  INTENT_UPDATE_DATA,
  INTENT_CHANGE_CHART_TYPE,
  INTENT_EXPLAIN_CHART,
  INTENT_UNKNOWN
] as const;

export const DEFAULT_PAGE_CONTEXT = { source: "copilotkit" } as const;
export const DEFAULT_USER_CONTEXT = { userId: "u_demo", tenantId: "t_demo" } as const;

export const CHART_AGENT_CONTEXT_KEY = "chartAgentContext";
export const WINDOW_CHART_AGENT_CONTEXT_KEY = "__CHART_AGENT_CONTEXT__";
export const WINDOW_CHART_AGENT_FETCH_PATCHED_KEY = "__CHART_AGENT_FETCH_PATCHED__";
export const COPILOT_AGENT_RUN_METHOD = "agent/run";
