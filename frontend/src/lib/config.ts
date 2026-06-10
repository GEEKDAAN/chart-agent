export const copilotRuntimeUrl = import.meta.env.VITE_COPILOT_RUNTIME_URL?.trim() || "";

export const isCopilotEnabled = copilotRuntimeUrl.length > 0;
