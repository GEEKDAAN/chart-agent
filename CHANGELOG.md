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

## [0.10.1] - 2026-06-12

- 【前端】：
  1. 修复 CopilotKit Runtime 上下文补丁只匹配 `/copilotkit` 单端点的问题，现在 `/copilotkit/agent/{agentId}/run` 等子路径请求也会注入 `currentChart`。
  2. 修复 REST Agent run 请求体没有 `method=agent/run` 时上下文被写入错误结构的问题，确保连续追问能携带当前图表。
  3. 更新前端版本号和界面版本标识为 `0.10.1`。

- 【后端】：
  1. 开发模式下新增 CopilotKit Runtime 上下文诊断日志，输出 `hasCurrentChart`，便于确认真实请求是否携带当前图表上下文。
  2. 新增 `CHART_AGENT_ENV` 配置，生产环境为 `production` 时不输出该诊断日志。
  3. 修复 LLM-first 决策在已存在 `currentChart` 时误将“有哪些渠道？”等当前图表追问判断为澄清请求的问题；当确定性 fallback 明确识别为当前图表问答时，后端会拒绝冲突的 LLM 决策并回退到 `answer_current_chart_question`。
  4. 更新 FastAPI 应用版本为 `0.10.1`。

- 【测试】：
  1. 新增 CopilotKit REST Agent run 当前图表追问测试，覆盖“渠道有哪些？”这类连续问答不会触发进度卡或新图表 action。
  2. 新增 LLM 误判澄清请求时的回退测试，覆盖当前图表追问不会被错误澄清。

## [0.10.0] - 2026-06-12

- 【后端】：
  1. 新增 `ChartAgentDecision` 内部决策协议，包含 `intent`、`toolName`、`arguments`、`confidence`、`reason` 和 `source`。
  2. 新增 LLM-first 工具决策层：优先由大模型输出结构化工具决策，非法、低置信度或不可用时回退到确定性 fallback。
  3. LangGraph 入口从规则式 `classify_intent` 收敛为 `decide_tool`，`classify_intent` 仅保留为兼容入口。
  4. 当前图表追问改为读取 `currentChart` 回答，例如“有哪些渠道？”和“抖音的销售额有多少？”，不再误触发新图表生成。
  5. CopilotKit Runtime 的进度卡预判复用同一决策层，当前图表问答不输出 `chartAgentProgress` 或 action marker。
  6. 更新 FastAPI 应用版本为 `0.10.0`。
- 【前端】：
  1. 更新前端版本号和界面版本标识为 `0.10.0`。
  2. 保持 CopilotKit 定位为聊天 UI、上下文传递和工具渲染入口，暂不注册业务型 `useFrontendTool`。
- 【测试】：
  1. 新增 LLM 决策接管、非法决策回退、低置信度回退相关 workflow 测试。
  2. 新增图表 API 和 CopilotKit Runtime 测试，覆盖当前图表维度枚举和单项指标查询。
  3. 更新 Playwright E2E 测试，覆盖生成图表后的连续追问和问答不展示步骤卡。

## [0.9.9] - 2026-06-11

- 【后端】：
  1. 新增 `smalltalk`、`help`、`out_of_scope` 和 `unclear_chart_request` 意图分流，避免所有输入都强行进入图表 workflow。
  2. “你好”“你能做什么”等输入会返回普通文本回复，不触发图表 action，也不调用 LLM action 生成。
  3. 意图分类开始使用当前 `ChartSpec` 上下文，有图表时“这个图怎么样”“图表相关信息”“帮我看看”等请求会进入当前图表解释。
  4. CopilotKit Runtime 仅在生成或修改图表时输出 `chartAgentProgress` 工具调用，当前图表问答、闲聊、帮助和边界提示不再展示执行步骤卡。
  5. 更新 FastAPI 应用版本为 `0.9.9`。
- 【前端】：
  1. 更新前端版本号和界面版本标识为 `0.9.9`。
- 【测试】：
  1. 新增图表 API 测试，覆盖闲聊、帮助、非图表问题和模糊需求。
  2. 新增 workflow 测试，确认闲聊不会查询指标，也不会调用 LLM action 生成。
  3. 新增当前图表问答测试，确认 CopilotKit 传入 `currentChart` 后会解释当前图表而不是追问指标维度。
  4. 新增 CopilotKit Runtime 测试，确认闲聊只返回普通文本，不输出进度工具调用和 action marker。

## [0.9.8] - 2026-06-11

- 【前端】：
  1. 新增 `useRenderTool` 渲染器 `chartAgentProgress`，在 CopilotKit 原生聊天消息内展示结构化执行步骤。
  2. 移除主工作区外置步骤面板，避免执行状态脱离 CopilotKit 对话上下文。
  3. 新增 `zod` 显式依赖，用于维护 CopilotKit 工具渲染参数 schema。
  4. 更新前端版本号和界面版本标识为 `0.9.8`。
- 【后端】：
  1. CopilotKit `agent/run` SSE 改为输出 AG-UI `TOOL_CALL_START`、`TOOL_CALL_ARGS`、`TOOL_CALL_END` 和 `TOOL_CALL_RESULT` 事件，供前端 `useRenderTool` 原生渲染。
  2. 移除普通文本形式的“执行状态”输出和 `chart-agent-step` 隐藏 marker，保留 `chart-agent-action` 隐藏 action marker 用于自动应用图表变更。
  3. 更新 FastAPI 应用版本为 `0.9.8`。
- 【测试】：
  1. 更新 CopilotKit Runtime 测试，覆盖工具调用事件输出和旧状态文本不再输出。
  2. 更新 Playwright E2E 测试，校验步骤在 CopilotKit 聊天内展示、图表生成编辑、上下文传递和隐藏 marker 不外显。

## [0.9.7] - 2026-06-11

- 【前端】：
  1. 新增 Playwright 浏览器端到端测试，覆盖 CopilotKit 侧边栏生成图表、切换图表类型、修改样式、新增指标和解释图表的完整链路。
  2. 新增 `npm run test:e2e` 脚本和 `playwright.config.ts`，测试时可自动启动或复用本地前后端服务。
  3. 更新前端版本号和界面版本标识为 `0.9.7`。
- 【后端】：
  1. 更新 FastAPI 应用版本为 `0.9.7`。
- 【测试】：
  1. E2E 测试会校验 CopilotKit Runtime REST 请求、当前图表上下文传递、图表 canvas 渲染、执行状态展示和隐藏 action 标记不外显。
  2. 测试默认使用 `CHART_AGENT_LLM_MODE=off`，避免本地自动化验证依赖外部 LLM 网络和额度。
- 【文档】：
  1. 补充前端 E2E 自动化测试运行说明、端口环境变量和已知注意事项。
- 【工程】：
  1. 将 Playwright 本地测试产物加入 `.gitignore`，避免误提交临时报告和失败截图。

## [0.9.6] - 2026-06-11

- 【后端】
  1. 新增 `GET /copilotkit/info` Runtime Info 端点，兼容 CopilotKit 前端初始化时的直接信息探测请求。
  2. 新增 `POST /copilotkit/agent/{agent_id}/run` 和 `POST /copilotkit/agent/{agent_id}/connect`，兼容 CopilotKit 前端在 Runtime Info 探测成功后的 REST Agent 调用路径。
  3. 保留 `POST /copilotkit` 的 single-endpoint 入口，避免破坏现有调用方式。
  4. 更新 FastAPI 应用版本为 `0.9.6`。

- 【前端】
  1. 新增前端 favicon，避免浏览器默认请求 `/favicon.ico` 产生 404 噪音。
  2. 更新前端版本号和界面版本标识为 `0.9.6`。

- 【测试】
  1. 新增 `/copilotkit/info` 测试，覆盖响应结构和 Runtime 版本响应头。
  2. 新增 CopilotKit REST Agent run/connect 测试，覆盖前端真实调用路径。

## [0.9.5] - 2026-06-11

- 【后端】
  1. 将 CopilotKit `agent/run` 响应改为生成器式 SSE，避免等待 ChartAgent workflow 完成后才一次性返回。
  2. 在 CopilotKit 侧边栏消息中输出执行状态，包括需求解析、上下文读取、workflow 运行、图表同步和失败原因。
  3. 更新 FastAPI 应用版本为 `0.9.5`。

- 【前端】
  1. 继续复用 CopilotKit 原生侧边栏展示执行过程，不新增普通对话框或额外交互入口。
  2. 更新前端版本号和界面版本标识为 `0.9.5`。

- 【测试】
  1. 补充 CopilotKit Runtime 成功流测试，确认 SSE 响应中包含执行状态。
  2. 补充缺少用户消息时的失败流测试，确认返回失败状态和 `RUN_ERROR`。

## [0.9.4] - 2026-06-11

- 【前端】
  1. 将 CopilotKit 接入切换到 v2 组件入口，使用 `CopilotKitProvider`、`CopilotSidebar`、`useAgentContext` 和 `useAgent` 统一处理侧边栏消息、上下文和运行状态。
  2. 显式绑定 `chart-agent` Agent，并通过 v2 建议词配置维护图表生成和编辑快捷指令。
  3. 调整 TypeScript 模块解析为 `Bundler`，支持 CopilotKit v2 子路径类型解析。
  4. 更新前端版本号和界面版本标识为 `0.9.4`。

- 【后端】
  1. 收敛 `/copilotkit` 为 CopilotKit v2 single-endpoint Runtime，只保留 `info`、`agent/connect` 和 `agent/run`。
  2. 移除旧 GraphQL Runtime 兼容分支，避免保留未使用的 `availableAgents`、`loadAgentState` 和 `generateCopilotResponse` 入口。
  3. 补齐 `agent/connect` SSE 生命周期响应，确保侧边栏初始化连接可正常完成。
  4. 更新 FastAPI 应用版本为 `0.9.4`。

- 【测试】
  1. 重写 CopilotKit Runtime 测试，覆盖 `info`、`threads`、`agent/connect`、`agent/run`、当前图表上下文传递和未知 method。
  2. 完整后端测试通过，前端生产构建通过。

## [0.9.3] - 2026-06-11

- 【前端】
  1. 移除主界面的普通对话框和快捷提示按钮，统一使用 CopilotKit 侧边栏作为自然语言交互入口。
  2. CopilotKit 侧边栏默认展开，空图表状态提示用户通过侧边栏生成图表。
  3. 更新前端版本号和界面版本标识为 `0.9.3`。

- 【后端】
  1. 放宽本地 Vite 端口 CORS 规则，支持 `localhost/127.0.0.1` 的 `517x` 开发端口访问 `/copilotkit`。
  2. 补齐 CopilotKit single-endpoint Runtime Info 响应，避免前端启动时报 `runtime_info_fetch_failed`。
  3. 更新 FastAPI 应用版本为 `0.9.3`。

- 【测试】
  1. 新增 `/copilotkit` 本地 Vite 端口 CORS 预检测试。
  2. 新增 CopilotKit Runtime Info 响应结构测试。

- 【文档】
  1. 更新前端和根 README，明确当前版本不再保留普通对话框 fallback。

## [0.9.2] - 2026-06-11

- 【前端】
  1. Vite 开发服务器代理新增 `VITE_BACKEND_PROXY_URL` 配置，方便本地选择当前后端端口。
  2. 更新 `frontend/.env.example` 和前端说明文档，补充后端代理配置。
  3. 更新前端版本号和界面版本标识为 `0.9.2`。

## [0.9.1] - 2026-06-10

- 【前端】
  1. 新增 CopilotKit Runtime 上下文桥接，将当前图表、页面上下文和用户上下文同步到 Runtime 请求体。
  2. 将当前图表上下文注册为 CopilotKit readable context，提升侧边栏对当前图表状态的可见性。
  3. 更新前端版本号和界面版本标识为 `0.9.1`。
- 【后端】
  1. 加固 `/copilotkit` 上下文解析，兼容 `variables.properties`、`data.properties`、`metadata.chartAgentContext` 等多种请求结构。
  2. 支持从消息隐藏标记中解析 chart-agent 上下文，作为 Runtime 请求结构变化时的兜底路径。
  3. 更新 FastAPI 应用版本为 `0.9.1`。
- 【测试】
  1. 新增 CopilotKit Runtime 上下文兼容测试，覆盖 metadata 和 data properties 两种上下文传递路径。

## [0.9.0] - 2026-06-10

- 【后端】
  1. 新增独立数据需求解析服务，支持从用户输入中识别指标、维度、筛选条件和简单时间范围。
  2. 修正“看各渠道订单数”“看各地区利润率”等创建图表请求被误判为更新数据的问题。
  3. 创建图表时根据主指标动态设置图表标题和 y 轴编码，不再固定为销售额。
  4. 扩展 mock 指标源对 `time_range.start/end` 的支持，并补充地区筛选在渠道维度下的 mock 行为。
  5. 更新 FastAPI 应用版本为 `0.9.0`。
- 【测试】
  1. 新增数据需求解析单元测试，覆盖销售额、订单数、利润率、地区、渠道和最近 N 天场景。
  2. 新增 LangGraph workflow 集成测试，验证解析结果会正确传入指标查询节点。
  3. 新增指标服务时间范围和地区筛选测试。
- 【文档】
  1. 更新根 `README.md` 和 `backend/README.md`，说明确定性数据需求解析能力和后续 LLM 扩展边界。

## [0.8.0] - 2026-06-10

- 【后端】
  1. 将 mock 指标能力重构为 `MetricService`、`MetricCatalog` 和 `MetricDataSource` 边界。
  2. 保持 `get_metric_catalog`、`validate_data_access` 和 `query_metrics` 兼容，Agent workflow 无需改动。
  3. 支持按 `time_range.end` 生成稳定日期维度 mock 数据，并限制单次查询最大返回 500 行。
  4. 更新 FastAPI 应用版本为 `0.8.0`。
- 【测试】
  1. 新增指标服务层测试，覆盖指标目录、权限校验、过滤、limit、日期范围和可替换数据源。
- 【文档】
  1. 更新根 `README.md` 和 `backend/README.md`，说明可替换指标服务层和后续接真实数据源的扩展边界。

## [0.7.1] - 2026-06-10

- 【文档】
  1. 补充 CopilotKit 本地联调说明，明确推荐用独立后端端口验证当前代码。
  2. 说明 `CHART_AGENT_LLM_MODE=off` 的稳定联调用途，以及本地 `.env` 文件不能提交真实密钥。

## [0.7.0] - 2026-06-10

- 【前端】
  1. 新增 CopilotKit 消息桥接逻辑，可识别后端返回的 `ChartAgentAction` 标记。
  2. CopilotKit 侧边栏生成或编辑图表后，会复用现有 `applyChartAction` 自动刷新图表。
  3. 自动应用失败时会在状态栏显示错误信息。
  4. 更新前端版本号和界面版本标识为 `0.7.0`。

- 【后端】
  1. `/copilotkit` 响应新增不可见 `ChartAgentAction` 标记，用于前端安全解析和应用。
  2. 更新 FastAPI 应用版本为 `0.7.0`。

- 【测试】
  1. 更新 CopilotKit Runtime API 测试，校验 action 标记可解析，并覆盖上下文编辑 action。

- 【文档】
  1. 更新根 `README.md`、`backend/README.md` 和 `frontend/README.md`，说明 CopilotKit 自动应用能力和剩余边界。

## [0.6.0] - 2026-06-10

- 【前端】
  1. CopilotKit 请求新增 `currentChart`、`pageContext` 和 `userContext` 运行时上下文。
  2. 侧边栏上下文指令可以传递当前图表状态到后端 Runtime。
  3. 更新前端版本号和界面版本标识为 `0.6.0`。

- 【后端】
  1. 新增 `/copilotkit` Runtime 兼容端点。
  2. 支持 CopilotKit `availableAgents`、`loadAgentState` 和 `generateCopilotResponse` 操作。
  3. 将 CopilotKit 用户消息转接到现有 `ChartAgent` workflow。
  4. 返回 CopilotKit GraphQL Runtime 兼容的 assistant 文本响应。

- 【测试】
  1. 新增 CopilotKit Runtime API 测试，覆盖 agent 列表、状态加载、消息生成和当前图表上下文传递。

- 【文档】
  1. 更新根 `README.md`、`backend/README.md` 和 `frontend/README.md`，说明 Runtime 当前能力边界。

## [0.5.0] - 2026-06-10

- 【前端】
  1. 新增可选 CopilotKit 侧边栏组件。
  2. 新增 `VITE_COPILOT_RUNTIME_URL` 配置，未配置时默认不加载侧边栏。
  3. 将 CopilotKit 代码 lazy loading，保留现有普通输入框作为稳定 fallback。
  4. 新增 `frontend/.env.example`。
  5. 更新前端版本号为 `0.5.0`。

- 【文档】
  1. 更新根 `README.md`，标记 CopilotKit 前端侧边栏为可选能力。
  2. 更新 `frontend/README.md`，补充 CopilotKit 配置说明。

## [0.4.1] - 2026-06-10

- 【后端】
  1. 新增 `OPENAI_BASE_URL` 配置，支持 OpenAI-compatible 服务地址。
  2. 新增 `backend/.env` 自动加载能力，便于本地测试 LLM 配置。
  3. 新增 OpenAI-compatible Chat Completions JSON fallback。
  4. 兼容 Windows UTF-8 BOM 格式的 `.env` 文件。
  5. 新增 `python-dotenv` 依赖。

- 【测试】
  1. 新增配置读取测试，覆盖 `CHART_AGENT_LLM_MODE`、`OPENAI_API_KEY`、`OPENAI_MODEL` 和 `OPENAI_BASE_URL`。

- 【文档】
  1. 更新 `backend/README.md`，补充 OpenAI-compatible 服务配置示例。

- 【工程】
  1. 修正 `.gitignore` 中通用 `lib/` 规则误忽略 `frontend/src/lib/` 的问题。

## [0.4.0] - 2026-06-10

- 【后端】
  1. 新增可选 OpenAI LLM action 生成能力。
  2. 新增 `CHART_AGENT_LLM_MODE`、`OPENAI_API_KEY`、`OPENAI_MODEL` 配置。
  3. 在 LangGraph `generate_action` 节点中加入 LLM 优先、确定性逻辑 fallback 的执行策略。
  4. 新增 LLM 输出校验，确保模型输出仍然落在 `ChartAgentAction` 协议内。
  5. 新增 `backend/.env.example` 配置示例。

- 【测试】
  1. 新增 LLM action 被采用的 workflow 测试。
  2. 新增 LLM 异常时自动回退确定性 action 的测试。

- 【文档】
  1. 更新根 `README.md`，标记 OpenAI API 为可选能力。
  2. 更新 `backend/README.md`，补充 LLM 配置和 fallback 行为说明。

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
