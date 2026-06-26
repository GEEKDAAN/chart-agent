export const CHART_AGENT_ID = "chart-agent";

export const CHART_AGENT_ACTION_TOOL = "chartAgentAction";
export const CHART_AGENT_PROGRESS_TOOL = "chartAgentProgress";

export const AGUI_RUN_STARTED_EVENT = "RUN_STARTED";
export const AGUI_RUN_FINISHED_EVENT = "RUN_FINISHED";
export const AGUI_RUN_ERROR_EVENT = "RUN_ERROR";
export const AGUI_TEXT_MESSAGE_START_EVENT = "TEXT_MESSAGE_START";
export const AGUI_TEXT_MESSAGE_CONTENT_EVENT = "TEXT_MESSAGE_CONTENT";
export const AGUI_TEXT_MESSAGE_END_EVENT = "TEXT_MESSAGE_END";
export const AGUI_TOOL_CALL_START_EVENT = "TOOL_CALL_START";
export const AGUI_TOOL_CALL_ARGS_EVENT = "TOOL_CALL_ARGS";
export const AGUI_TOOL_CALL_RESULT_EVENT = "TOOL_CALL_RESULT";
export const AGUI_TOOL_CALL_END_EVENT = "TOOL_CALL_END";

export const ACTION_CREATE_CHART = "create_chart";
export const ACTION_UPDATE_CHART = "update_chart";
export const ACTION_ERROR = "error";

export const INTENT_CREATE_CHART = "create_chart";
export const INTENT_UPDATE_STYLE = "update_style";
export const INTENT_UPDATE_DATA = "update_data";
export const INTENT_CHANGE_CHART_TYPE = "change_chart_type";

export const UI_BLOCK_METRIC_SUMMARY = "metric_summary";
export const UI_BLOCK_INSIGHT_CARD = "insight_card";
export const UI_BLOCK_SUGGESTED_ACTIONS = "suggested_actions";
export const UI_BLOCK_DATA_TABLE = "data_table";

export const CHART_AGENT_UI_BLOCK_TYPES = [
  UI_BLOCK_METRIC_SUMMARY,
  UI_BLOCK_INSIGHT_CARD,
  UI_BLOCK_SUGGESTED_ACTIONS,
  UI_BLOCK_DATA_TABLE
] as const;

export const CHART_AGENT_BACKEND_CHAT_PATH = "/chart-agent/chat";
export const CHART_AGENT_CONTEXT_KEY = "chartAgentContext";
export const CHART_AGENT_CONTEXT_MARKER_PREFIX = "<!-- chart-agent-context:";
export const DEFAULT_BACKEND_URL = "http://127.0.0.1:8000";

export const DEFAULT_PAGE_CONTEXT = { source: "copilotkit-official-runtime-poc" } as const;
export const DEFAULT_USER_CONTEXT = { userId: "copilotkit_user", tenantId: "demo" } as const;
