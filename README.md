# chart-agent

Conversational chart generation and editing system built around a controlled `ChartSpec` protocol.

## Goal

`chart-agent` lets users create and edit charts through natural language while keeping rendering, data access, and model output bounded by explicit schemas.

The core design principle is:

- The model generates `ChartSpec`, `ChartPatch`, or `ChartAgentAction`.
- The frontend validates and converts `ChartSpec` into ECharts options.
- The backend coordinates intent routing, semantic metric access, permissions, and output validation.
- The agent never writes SQL directly and never generates arbitrary React components or ECharts options.

## Planned Stack

- React + Vite
- CopilotKit
- ECharts
- FastAPI
- LangGraph
- Python semantic metric layer

## Repository Layout

```text
backend/   FastAPI, LangGraph agent, schemas, validators, and metric tools
frontend/  React app, CopilotKit integration, ChartSpec runtime, and ECharts rendering
docs/      Architecture notes and product design documents
```

## MVP Scope

- Single-chart creation
- Single-chart editing
- Controlled chart schema
- Mock metric catalog and mock query service
- Non-streaming JSON response first
- Streaming events after the core loop is stable

## Out of Scope for MVP

- Multi-chart dashboards
- Chart persistence and sharing
- Drill-down workflows
- Multi-agent orchestration
- Direct SQL generation by the agent
- Direct ECharts option generation by the model
