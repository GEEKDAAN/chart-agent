# Changelog

This file records meaningful changes for each project version.

## Maintenance Format

Use one entry per version. Keep the newest version at the top.

```md
## [0.2.0] - YYYY-MM-DD

- 【前端】
  1. ...
  2. ...

- 【后端】
  1. ...

- 【文档】
  1. ...

- 【工程】
  1. ...
```

Only include sections that changed in that version. Prefer clear user-facing or engineering-impact descriptions instead of raw commit messages.

## Versioning Rules

This project uses `major.minor.patch`:

- New independent module or capability: increment `minor`, for example `0.1.0 -> 0.2.0`.
- Change or improve existing behavior: increment `patch`, for example `0.2.0 -> 0.2.1`.
- Breaking protocol, API, or architecture change: increment `major`, for example `0.9.0 -> 1.0.0`.

## [0.1.1] - 2026-06-09

- 【文档】
  1. Added `CHANGELOG.md` as the project change record.
  2. Defined the changelog maintenance format and versioning rules.
  3. Added a README pointer to the changelog maintenance process.

## [0.1.0] - 2026-06-09

- 【前端】
  1. Initialized the `frontend/` directory.
  2. Reserved the frontend workspace for React, CopilotKit, ChartSpec runtime, and ECharts rendering.

- 【后端】
  1. Initialized the `backend/` directory.
  2. Reserved the backend workspace for FastAPI, LangGraph Agent, schemas, validators, and metric tools.

- 【文档】
  1. Added project overview and MVP scope in `README.md`.
  2. Added architecture notes in `docs/architecture.md`.
  3. Added the original chart agent design document in `docs/chart-agent-design.md`.

- 【工程】
  1. Initialized the Git repository and connected it to the GitHub remote.
  2. Added `.gitignore` rules for Python, Node, editor files, and local workspace artifacts.
