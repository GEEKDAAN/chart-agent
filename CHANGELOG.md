# 更新日志

本文档用于记录项目每个版本的重要变更。

## 维护格式

每个版本使用一个独立条目，最新版本放在最上方。

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

只保留本版本实际发生变更的模块。描述应说明用户可感知的变化或工程影响，不直接堆叠原始 commit message。

## 版本规则

项目采用 `major.minor.patch` 版本格式：

- 新增独立模块或能力：`minor +1`，例如 `0.1.0 -> 0.2.0`。
- 修改或增强已有能力：`patch +1`，例如 `0.2.0 -> 0.2.1`。
- 发生破坏性协议、API 或架构变化：`major +1`，例如 `0.9.0 -> 1.0.0`。

## [0.3.0] - 2026-06-10

- 【后端】
  1. 新增 LangGraph 版 `ChartAgent` workflow。
  2. 将原规则版 Agent 入口迁移为 `classify_intent -> plan_data -> query_data -> generate_action -> validate_action -> respond` 节点编排。
  3. 保持 `/chart-agent/chat` 外部接口兼容。
  4. 新增可注入的 `query_metrics` 依赖，便于验证样式修改不会触发数据查询。

- 【测试】
  1. 新增后端 pytest 测试。
  2. 覆盖创建图表、修改颜色、新增利润率、切换图表类型、缺少当前图表时报错等场景。
  3. 覆盖 LangGraph workflow 中样式修改不查数、创建图表查数一次的行为。

- 【文档】
  1. 更新根 `README.md`，标记 LangGraph 已接入。
  2. 更新 `backend/README.md`，补充 Agent workflow 和测试命令。

## [0.2.0] - 2026-06-09

- 【前端】
  1. 新增 React + Vite 前端 MVP 工程。
  2. 新增 `ChartSpec` 类型、校验、patch 合并和 action 应用逻辑。
  3. 新增 ECharts option 转换和图表渲染组件。
  4. 新增对话输入界面和快捷示例指令。

- 【后端】
  1. 新增 FastAPI 后端 MVP 工程。
  2. 新增 `ChartSpec`、`ChartPatch`、`ChartAgentAction` 等协议模型。
  3. 新增 `/chart-agent/chat` 接口。
  4. 新增 mock 指标目录、mock 指标查询和基础权限校验。
  5. 新增规则版 ChartAgent 路由，支持创建图表、改颜色、加指标、换图表类型和解释图表。

- 【文档】
  1. 将根 `README.md` 调整为中文为主的项目说明。
  2. 新增前端和后端本地运行说明。
  3. 新增 `backend/README.md` 和 `frontend/README.md`。

## [0.1.2] - 2026-06-09

- 【文档】
  1. 将更新日志维护说明和历史记录统一调整为中文。
  2. 将 `README.md` 中的更新日志说明调整为中文。

## [0.1.1] - 2026-06-09

- 【文档】
  1. 新增 `CHANGELOG.md` 作为项目更新记录。
  2. 定义更新日志维护格式和版本规则。
  3. 在 `README.md` 中增加更新日志维护说明。

## [0.1.0] - 2026-06-09

- 【前端】
  1. 初始化 `frontend/` 目录。
  2. 预留 React、CopilotKit、ChartSpec runtime 和 ECharts 渲染相关的前端工作区。

- 【后端】
  1. 初始化 `backend/` 目录。
  2. 预留 FastAPI、LangGraph Agent、schema、validator 和指标工具相关的后端工作区。

- 【文档】
  1. 在 `README.md` 中添加项目概览和 MVP 范围。
  2. 在 `docs/architecture.md` 中添加架构说明。
  3. 添加原始图表 Agent 设计文档 `docs/chart-agent-design.md`。

- 【工程】
  1. 初始化 Git 仓库并连接 GitHub 远程仓库。
  2. 添加 `.gitignore`，覆盖 Python、Node、编辑器文件和本地工作区产物。
