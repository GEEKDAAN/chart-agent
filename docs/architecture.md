# chart-agent Architecture

## Overview

`chart-agent` is a conversational chart generation and editing system. Users describe analytical intent in natural language, and the backend returns structured chart actions that the frontend validates and renders.

The system intentionally avoids letting the model generate executable UI, arbitrary ECharts options, or SQL. Model output is constrained to stable contracts.

## Main Components

- **React frontend**: owns page state, current `ChartSpec`, validation, patch merging, and ECharts rendering.
- **CopilotKit**: provides the conversational UI and exposes current chart context to the agent.
- **FastAPI backend**: receives chat requests and returns structured chart actions.
- **LangGraph ChartAgent**: routes intent, plans data needs, calls metric tools, generates actions, and validates output.
- **Metric tools**: expose a controlled semantic data interface through metric catalogs, access validation, and aggregate queries.
- **ECharts**: renders options derived by the frontend from validated `ChartSpec`.

## Data Flow

```text
User message
  -> CopilotKit UI
  -> React sends message + currentChart + pageContext
  -> FastAPI
  -> LangGraph ChartAgent
  -> metric catalog / mock query service
  -> ChartAgentAction
  -> backend validation
  -> React action handling
  -> frontend validation
  -> ChartSpec to ECharts option
  -> render
```

## MVP Backend Flow

```text
classify_intent
  -> plan_data_if_needed
  -> query_mock_metrics_if_needed
  -> generate_chart_action
  -> validate_chart_action
  -> respond
```

## Protocol Boundary

The backend returns `ChartAgentAction` values such as:

- `create_chart`
- `update_chart`
- `error`

The frontend applies these actions only after validation. `ChartPatch` should be narrower than `Partial<ChartSpec>` and must not allow unknown fields or chart ID mutation.

## Generative UI Direction

The project will evolve toward controlled generative UI. The model and backend agent must not generate executable React code, arbitrary HTML, or arbitrary ECharts options. Instead, the backend may return validated `uiBlocks` alongside `ChartAgentAction`.

`ChartAgentAction` remains the only protocol that can mutate chart state. `uiBlocks` are display-only enhancements for summaries, insights, suggested actions, and lightweight supporting views. React renders them through a whitelist of components, preferably inside CopilotKit messages via `useRenderTool`.

Detailed design: [Controlled Generative UI Design](generative-ui-design.md).

## Production Risks

- Weak metric catalog design can cause unstable or invalid data queries.
- Overly broad patches can corrupt chart state.
- Missing frontend validation can allow invalid model output to reach rendering.
- Server-side memory and client-side chart state can diverge unless the current chart is included in every request.
- Streaming should be added after the non-streaming contract is stable.
