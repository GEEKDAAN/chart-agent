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

## [0.11.26] - 2026-06-27

- 【前端】：
  1. 将生成式 UI 的 suggested action 从静态标签调整为可点击按钮。
  2. 点击 suggested action 后复用 CopilotKit 原生输入框发送自然语言请求，继续走 CopilotKit -> Runtime -> 后端 Agent 链路。
  3. 不新增普通聊天框，不注册业务型 `useFrontendTool`，避免形成第二条业务执行通道。

- 【工程】：
  1. 补充 Playwright E2E，验证点击“查看渠道”建议后会发送“有哪些渠道？”并基于当前图表回答。
  2. 更新前端、Runtime 和 FastAPI 版本号为 `0.11.26`。

## [0.11.25] - 2026-06-26

- 【后端】：
  1. 新增 `services/ui_blocks.py`，从受控 `ChartSpec` 确定性生成指标摘要、主要洞察和建议操作三类 UI Blocks。
  2. 创建图表成功后，`ChartAgentResponse.uiBlocks` 返回首批生成式 UI 展示内容；非创建图表动作继续返回空数组。
  3. UI Blocks 只作为展示增强，不改变 `ChartAgentAction` 作为图表状态变更唯一协议的边界。

- 【工程】：
  1. 新增后端 UI Blocks 服务测试，覆盖创建图表生成 blocks、非创建动作不生成 blocks。
  2. 更新 API 测试，验证创建图表响应包含 UI Blocks，当前图表问答不返回 UI Blocks。
  3. 更新前端、Runtime 和 FastAPI 版本号为 `0.11.25`。

## [0.11.24] - 2026-06-26

- 【Runtime】：
  1. 新增 `chartAgentUiBlocks` CopilotKit 工具事件发送能力，当后端响应包含非空 `uiBlocks` 时发送 `TOOL_CALL_START`、`TOOL_CALL_RESULT` 和 `TOOL_CALL_END`。
  2. 工具事件内容采用 `{ uiBlockId, blocks }` 结构，与前端 `useRenderTool(chartAgentUiBlocks)` 渲染器保持一致。
  3. `uiBlocks` 为空或缺失时不发送生成式 UI 工具事件，避免普通问答或无洞察响应出现空卡片。

- 【工程】：
  1. 新增 Runtime 单测覆盖非空 `uiBlocks` 会触发工具事件、空 `uiBlocks` 不触发工具事件。
  2. 保持 `chartAgentAction` 和 `chartAgentProgress` 现有行为不变，本阶段只打通生成式 UI 的 Runtime 事件链路。
  3. 更新前端、Runtime 和 FastAPI 版本号为 `0.11.24`。

## [0.11.23] - 2026-06-26

- 【前端】：
  1. 新增 `chartAgentUiBlocks` 的 CopilotKit `useRenderTool` 渲染器，支持指标摘要、洞察卡片、建议操作和轻量明细表四类受控 UI Block。
  2. 新增聊天消息内 UI Block 样式，保持与现有步骤面板一致的受控卡片视觉。
  3. suggested action 当前只做展示，不直接触发图表修改，后续仍需通过自然语言请求链路执行。

- 【工程】：
  1. 本版本只新增前端白名单渲染能力；Runtime 暂不发送 `chartAgentUiBlocks` 事件，现有 CopilotKit 行为不变。
  2. 更新前端、Runtime 和 FastAPI 版本号为 `0.11.23`。

## [0.11.22] - 2026-06-26

- 【后端】：
  1. 新增 `uiBlocks` 响应协议模型和 `backend/app/domain/ui_blocks.py` 常量入口，覆盖指标摘要、洞察卡片、建议操作和轻量明细表四类受控 UI Block。
  2. `ChartAgentResponse` 新增可选扩展字段 `uiBlocks`，当前默认返回空数组，不改变现有图表生成、编辑和问答行为。
  3. 新增 UI Block schema 测试，校验非法 block type 和缺失必要 payload 会被拒绝。

- 【前端】：
  1. 新增 UI Block 类型和常量定义，为后续白名单渲染器做准备。
  2. 本阶段只识别协议类型，不渲染 UI Blocks。

- 【Runtime】：
  1. 新增 UI Block 类型常量和后端响应类型扩展。
  2. 本阶段不新增 `chartAgentUiBlocks` 工具事件，保持 CopilotKit 行为不变。

- 【工程】：
  1. 更新前端、Runtime 和 FastAPI 版本号为 `0.11.22`。

## [0.11.21] - 2026-06-26

- 【文档】：
  1. 新增 `docs/generative-ui-design.md`，明确项目生成式 UI 采用受控 UI Blocks 路线。
  2. 补充架构、CopilotKit 工具事件、前端工程规范和后端工程规范中的生成式 UI 边界。
  3. 明确 `ChartAgentAction` 仍是图表状态变更的唯一协议，`uiBlocks` 只用于洞察、摘要、建议操作和辅助展示。

- 【工程】：
  1. 生成式 UI 文档阶段在 `codex/generative-ui` 分支进行，不直接在 `main` 上开发。
  2. 本版本只做文档规划，不改变前后端协议和业务行为。
  3. 更新前端、Runtime 和 FastAPI 版本号为 `0.11.21`。

## [0.11.20] - 2026-06-26

- 【后端】：
  1. 新增后端测试自动隔离配置，单测默认强制关闭 LLM 模式并清理 `get_settings` 缓存。
  2. 避免本地 `backend/.env` 中的大模型配置污染单测，防止测试误触发真实 LLM 网络请求。

- 【工程】：
  1. 后端测试耗时从约 4 分 51 秒降至约 2.37 秒。
  2. 更新前端、Runtime 和 FastAPI 版本号为 `0.11.20`。

## [0.11.19] - 2026-06-26

- 【后端】：
  1. 补充后端 `domain` 常量入口，集中管理 action error code、chart type、column type 和决策来源。
  2. 将 `ChartSpec`、`ChartAgentAction`、`ChartAgentDecision` 的 schema 类型声明改为从后端领域常量派生，减少协议字符串重复。
  3. 将后端 fallback/LLM 决策来源和核心 Agent 错误码改为常量引用，降低后续维护时的魔法值风险。

- 【工程】：
  1. 更新前端、Runtime 和 FastAPI 版本号为 `0.11.19`。
  2. 本版本只做后端协议常量治理，不改变 CopilotKit 对话、上下文传递或图表 action 行为。

## [0.11.18] - 2026-06-25

- 【前端】：
  1. 新增 `frontend/src/domain/chartAgentProtocol.ts`，集中管理前端版本号、CopilotKit agent id、工具名、action type、chart type、column type、intent 和默认运行上下文。
  2. 将 CopilotKit 工具渲染、ChartSpec 校验、Runtime 上下文注入和 action 应用逻辑中的高频协议字符串迁移为常量引用。

- 【Runtime】：
  1. 新增 `runtime/src/protocol.ts`，集中管理 Runtime agent id、工具名、action type、intent、后端接口路径、默认上下文和上下文 marker。
  2. 将 Runtime 事件发送、后端请求、进度模板和测试断言中的协议字符串迁移为常量引用。

- 【工程】：
  1. 更新前端、Runtime 和 FastAPI 版本号为 `0.11.18`。
  2. 本版本只做前端与 Runtime 协议常量治理，不改变 CopilotKit 聊天、上下文传递或图表应用行为。

## [0.11.17] - 2026-06-24

- 【后端】：
  1. 将原 `app/services/llm_decisions.py` 拆分为 `app/services/decision/` 子模块，分别承载 fallback 决策、LLM 决策调用、决策校验、当前图表问答和图表 schema 匹配。
  2. 保留 `app.services.llm_decisions` 作为兼容入口，现有图谱调用和测试 monkeypatch 路径不需要调整。
  3. 本次拆分不改变意图识别、图表问答和 LLM guardrail 的业务行为，目标是降低后续维护成本。

- 【工程】：
  1. 更新前端、Runtime 和 FastAPI 版本号为 `0.11.17`。

## [0.11.16] - 2026-06-24

- 【后端】：
  1. 新增 `backend/app/domain/` 常量模块，集中管理 action、chart type、column type、intent/tool、metric、dimension、color 和 visibility 相关业务常量。
  2. 将数据需求解析、LLM 决策、图表 action 生成、指标服务、样式修改和显示隐藏逻辑中的高频魔法值迁移为 domain 常量引用。
  3. 保留对外 API 和 ChartSpec/ChartAgentAction 协议不变，本版本只做后端结构治理和可维护性增强。

- 【工程】：
  1. 更新前端、Runtime 和 FastAPI 版本号为 `0.11.16`。

## [0.11.15] - 2026-06-24

- 【文档】：
  1. 新增根目录 `AGENTS.md`，作为人类开发者和 AI Agent 的项目协作规则入口。
  2. 新增后端工程规范，明确 FastAPI、LangGraph、services、schemas 和 domain 常量的分层边界。
  3. 新增前端工程规范，明确 CopilotKit、ChartSpec、ECharts 渲染和前端状态同步的职责边界。
  4. 新增测试规范，整理后端、Runtime、前端构建、Playwright E2E 和中文编码检查的适用场景。
  5. 将“禁止新增未集中管理的魔法值”写入硬规则，要求 intent、toolName、chart type、action type、指标、维度、颜色和 progress step id 集中管理。

- 【工程】：
  1. 在根 README 中补充工程规范入口。
  2. 更新前端、Runtime 和 FastAPI 版本号为 `0.11.15`。
  3. 本版本只新增工程规范和版本元信息，不改变业务行为。

## [0.11.14] - 2026-06-24

- 【后端】：
  1. 新增意图决策矩阵测试，集中覆盖新建图表、当前图表问答、样式修改、隐藏/恢复显示、图表类型切换、数据更新、闲聊和越界请求。
  2. 收紧 LLM 冲突校验：当确定性逻辑明确识别为新图表请求时，LLM 不能改判为其他工具。
  3. 更新 LLM 工具决策提示，明确“与当前图表不同的新维度、新指标、时间范围组合”应选择 `create_chart`。

- 【前端】：
  1. 新增 CopilotKit 连续对话 E2E，验证“趋势图 -> 各渠道销售额图 -> 渠道追问”不会互相误判。
  2. E2E 测试新增工具结果解析，直接校验 `chartAgentAction` 返回的图表类型和 encoding。

## [0.11.13] - 2026-06-24

- 【后端】：
  1. 修复已有趋势图上下文下，“给我展示近30天各渠道的销售额”被误判为当前图表问答的问题。
  2. 新增新图表需求识别逻辑：当用户提出与当前图表不同的新维度或指标组合时，优先生成新图表。
  3. 增强 LLM 决策校验，当确定性逻辑明确识别为新图表请求时，拒绝 LLM 将其误判为当前图表问答。

- 【测试】：
  1. 新增当前趋势图切换到各渠道销售额图表的 API 测试。
  2. 新增 LLM 误判新图表请求为当前图表问答时的回退测试。
  3. 保留“有哪些渠道？”等当前图表追问仍走问答路径的回归测试。

## [0.11.12] - 2026-06-23

- 【后端】：
  1. 修复“除抖音外，其他改成绿色”这类排除式颜色修改被误解析为修改抖音的问题。
  2. 新增图表类目隐藏和恢复显示能力，支持“不要显示天猫”“恢复显示天猫”等请求，并通过受控 `hiddenValues` 样式 patch 保留原始数据。
  3. 当确定性解析明确识别为样式/显示范围修改时，拒绝 LLM 将请求误判为当前图表问答的决策。

- 【前端】：
  1. `ChartSpec.style` 新增 `hiddenValues` 支持，ECharts 图表和表格会按隐藏类目过滤显示。
  2. 图表 patch 合并时忽略后端响应中的 `null` 字段，避免局部样式更新意外清空已有颜色或显示设置。

- 【测试】：
  1. 新增排除式颜色修改、隐藏类目、恢复显示类目和 LLM 误判回退测试。

## [0.11.11] - 2026-06-23

- 【后端】：
  1. 增强样式修改解析，支持一次请求中同时修改多个图表类目的颜色，例如“微信改成红色，天猫变成绿色”。
  2. 扩展颜色识别范围，新增黄色、紫色、橙色、黑色、白色、灰色和粉色等颜色词。
  3. 样式修改改为优先走后端受控工具执行，避免 LLM action 直接生成错误颜色映射。
  4. 修复“天猫变成黄色”等请求被误判为当前图表问答并返回销售额的问题。

- 【测试】：
  1. 新增多目标颜色修改、黄色样式修改和 LLM 错误 action 不覆盖受控样式工具的测试。

## [0.11.10] - 2026-06-23

- 【前端】：
  1. 关闭 CopilotKit 前端开发控制台，减少生产页面中无关调试能力的加载面。
  2. 为 CopilotKit 默认 `streamdown` 富文本渲染器增加轻量纯文本替身，移除当前业务未使用的 Mermaid、Shiki、KaTeX 富文本渲染链路。
  3. 将 KaTeX 样式动态加载重定向为空模块，避免生产构建继续输出未使用的 KaTeX 字体资源。

- 【工程】：
  1. 保持 CopilotKit 聊天、上下文传递和 `useRenderTool` 工具卡能力不变，仅收敛前端生产构建依赖体积。

## [0.11.9] - 2026-06-22

- 【前端】：
  1. 为 Vite 增加 `@segment/analytics-node` 浏览器端空实现别名，避免 CopilotKit 前端构建间接打入 `node-fetch` 和 Node 内置模块外部化告警。
  2. 将 ECharts 单独拆分为独立生产 chunk，并按当前 CopilotKit 富文本依赖基线调整 chunk 告警阈值，消除无效的大包告警。

- 【工程】：
  1. 新增 Segment Analytics Node 浏览器端 no-op stub，确保前端生产构建不依赖 Node telemetry 包。

## [0.11.8] - 2026-06-22

- 【Runtime】：
  1. 增强 Node Runtime `/health`，检查 FastAPI 后端 `/health` 是否可达。
  2. FastAPI 不可达时 Runtime 健康检查返回 `503` 和 `degraded`，便于定位三服务链路问题。
  3. 新增 Runtime 健康检查单元测试，覆盖后端可达、后端异常和请求失败场景。

## [0.11.7] - 2026-06-22

- 【文档】：
  1. 新增 `docs/main-merge-checklist.md`，整理 Runtime PoC 分支合并回 `main` 前的差异、确认项、验证命令和合并后验收路径。
  2. 明确合并会删除 FastAPI 自研 CopilotKit Runtime，并引入 Node Runtime 三服务架构。

## [0.11.6] - 2026-06-22

- 【文档】：
  1. 新增 `docs/runtime-poc-merge-review.md`，整理 CopilotKit 官方 Runtime PoC 合并前审查结论、风险分级和验收标准。
  2. 明确当前分支适合作为主线候选基础，但仍需继续收敛上下文传递、真实流式进度和三服务部署说明。

## [0.11.5] - 2026-06-16

- 【工程】：
  1. 新增 `scripts/check-text-encoding.ps1`，扫描核心源码、测试和文档中的典型中文乱码片段。
  2. 为 Runtime 增加 `npm run check:text` 入口，便于在本地验证中文文案未被错误编码。
- 【前端】：
  1. 更新前端版本号和界面版本标识为 `0.11.5`。
- 【后端】：
  1. 更新 FastAPI 应用版本为 `0.11.5`。

## [0.11.4] - 2026-06-16

- 【Runtime】：
  1. 新增 Node Runtime 契约测试，覆盖当前图表上下文转发、图表生成/修改工具事件、当前图表问答无工具事件和后端异常回复。
  2. 新增 `npm run test` 测试入口，使用 Node test runner + `tsx` 执行 Runtime 测试。
- 【工程】：
  1. 更新前端、Runtime 和 FastAPI 版本号为 `0.11.4`。

## [0.11.3] - 2026-06-15

- 【工程】：
  1. 新增 `scripts/dev.ps1`，统一启动 FastAPI、Node Runtime 和 Vite 三个本地开发服务。
  2. 新增 `scripts/stop-dev.ps1`，根据 `tmp/dev-processes.json` 停止本地开发进程树。
  3. 修复后台 PowerShell 启动参数和停止脚本变量兼容问题，并生成可排查的临时启动脚本，提升 Windows 本地启动稳定性。
  4. 将 `tmp/` 加入 `.gitignore`，避免本地日志和进程文件进入版本库状态。
- 【文档】：
  1. 新增 `docs/local-development.md`，说明三服务职责、默认端口、LLM 模式、启动方式、停止方式和验收路径。
  2. 重写根 `README.md`，收敛当前官方 Runtime 分支的架构、启动方式、能力范围和测试入口。
  3. 更新 `runtime/README.md`、`frontend/README.md`、`docs/copilotkit-runtime-poc.md` 和 `docs/progress-protocol.md`，移除过期的隐藏 marker 和开始/完成快照描述。
- 【前端】：
  1. 更新前端版本号和界面版本标识为 `0.11.3`。
- 【后端】：
  1. 更新 FastAPI 应用版本为 `0.11.3`。

## [0.11.2] - 2026-06-15

- 【Runtime】：
  1. 新增 `chartAgentAction` 工具事件，用于传递后端返回的 `ChartAgentAction`，不再把图表动作塞进 assistant 文本隐藏注释。
  2. `chartAgentProgress` 继续只负责步骤面板，`chartAgentAction` 专门负责图表创建和修改动作，两个通道职责分离。
  3. assistant 文本回复收敛为纯自然语言内容，不再包含 `chart-agent-action` marker。
- 【前端】：
  1. 新增 `useRenderTool(chartAgentAction)` 接收器，根据工具结果应用图表动作，并通过 `actionId` 去重。
  2. 移除基于 assistant 消息扫描隐藏 marker 的动作桥接逻辑。
  3. 更新前端版本号和界面版本标识为 `0.11.2`。
- 【后端】：
  1. 更新 FastAPI 应用版本为 `0.11.2`。

## [0.11.1] - 2026-06-15

- 【Runtime】：
  1. 官方 CopilotKit Runtime 下的 `chartAgentProgress` 改为按后端最终 `intent` 输出多段快照，避免继续依赖前端文本预判。
  2. 生成图表、修改样式、修改数据和切换图表类型会在同一个工具卡内推进多个步骤，而不是只显示开始和完成两帧。
  3. 当前图表问答、闲聊、帮助和边界提示不创建步骤卡，减少普通问答被误识别为执行任务的割裂感。
- 【前端】：
  1. 更新前端版本号和界面版本标识为 `0.11.1`，继续复用 `useRenderTool(chartAgentProgress)` 渲染原生聊天内步骤面板。
- 【后端】：
  1. 更新 FastAPI 应用版本为 `0.11.1`。

## [0.11.0] - 2026-06-15

- 【Runtime】：
  1. 新增 `runtime/` Node 服务，使用官方 `@copilotkit/runtime/v2` + Express 接管 `/copilotkit` Runtime 入口。
  2. 新增自定义 AG-UI `ChartAgent`，将 CopilotKit 消息和当前图表上下文转发到 FastAPI `/chart-agent/chat`。
  3. 在 Node Runtime 中输出 `chartAgentProgress` 工具事件，继续复用前端 `useRenderTool` 步骤卡。

- 【后端】：
  1. FastAPI 不再挂载自研 `/copilotkit` Runtime router，只保留图表业务接口 `/chart-agent/chat`。
  2. 更新 FastAPI 应用版本为 `0.11.0`。

- 【前端】：
  1. Vite 代理拆分为 `VITE_BACKEND_PROXY_URL` 和 `VITE_COPILOT_RUNTIME_PROXY_URL`，分别指向 FastAPI 和 Node Runtime。
  2. 更新前端版本号和界面版本标识为 `0.11.0`。

- 【文档】：
  1. 新增 `docs/copilotkit-runtime-poc.md`，记录官方 Runtime SDK PoC 的可行性结论、限制和后续建议。
  2. 更新根 README、后端 README、前端 README 和进度协议文档，说明三服务本地运行拓扑。

- 【测试】：
  1. Playwright E2E 改为自动启动 FastAPI、Node Runtime 和前端三类服务。
  2. 验证官方 Runtime SDK 链路下图表生成、图表编辑、当前图表问答和步骤卡渲染仍可运行。

## [0.10.4] - 2026-06-14

- 【前端】：
  1. 将 CopilotKit Runtime SSE 进度观察逻辑拆分到 `copilotProgressObserver`，`copilotRuntimeContext` 只负责请求上下文注入。
  2. 更新前端版本号和界面版本标识为 `0.10.4`。

- 【后端】：
  1. 新增 `app.services.progress` 模块，集中维护 `chartAgentProgress` 步骤模板、LangGraph 节点映射、失败态和元数据封装。
  2. 精简 CopilotKit Runtime router，移除未使用的旧进度模板，路由只负责 Runtime 编排和 SSE 输出。
  3. 更新 FastAPI 应用版本为 `0.10.4`。

- 【文档】：
  1. 新增 `docs/progress-protocol.md`，说明 `chartAgentProgress` 的职责边界、payload、维护规则和当前限制。
  2. 在前端 README 中补充进度协议文档入口。

- 【测试】：
  1. 调整 Runtime 测试直接覆盖 `app.services.progress`，避免测试依赖 router 内部实现。

## [0.10.3] - 2026-06-14

- 【前端补充】：
  1. 新增 `chartAgentProgress` 本地进度 store，通过 `progressId` 让 CopilotKit 工具卡订阅后端流式进度快照。
  2. 新增进度快照队列播放机制，每个阶段保留最小可见时长，避免后端执行过快时页面只看到开始态和完成态。

- 【后端补充】：
  1. `chartAgentProgress` payload 新增 `sequence` 和 `isFinal`，用于前端去重、排序和识别最终快照。

- 【前端】：
  1. 更新前端版本号和界面版本标识为 `0.10.3`。
  2. 继续复用 CopilotKit `useRenderTool(chartAgentProgress)`，前端协议不变。

- 【后端】：
  1. CopilotKit Runtime 改为基于 LangGraph workflow 流式输出进度快照，同一个工具调用会随节点完成多次更新。
  2. 生成图表、修改样式、修改数据和切换图表类型会根据真实执行节点推进步骤状态。
  3. 执行失败时步骤卡会进入 `failed` 状态，避免失败请求显示为全部完成。
  4. 当前图表问答、闲聊、帮助和边界提示继续不输出步骤卡。
  5. 更新 FastAPI 应用版本为 `0.10.3`。

- 【测试】：
  1. 更新 CopilotKit Runtime 测试，确认一次请求会输出多次 `TOOL_CALL_RESULT` 进度快照。
  2. 新增失败态进度测试，覆盖没有当前图表时发起样式修改会展示 failed 步骤。

## [0.10.2] - 2026-06-14

- 【前端】：
  1. 更新前端版本号和界面版本标识为 `0.10.2`。
  2. 保持 CopilotKit `useRenderTool(chartAgentProgress)` 渲染协议不变，继续在原生聊天消息中展示步骤面板。

- 【后端】：
  1. CopilotKit Runtime 的 `chartAgentProgress` 改为按后端决策工具生成差异化步骤模板。
  2. `create_chart`、`update_style`、`update_data`、`change_chart_type` 分别展示符合当前任务语义的步骤，不再共用同一套固定流程。
  3. 当前图表问答、闲聊、帮助和边界提示继续不输出步骤卡，避免普通问答被误解为图表执行任务。
  4. 更新 FastAPI 应用版本为 `0.10.2`。

- 【测试】：
  1. 新增差异化步骤模板测试，覆盖生成图表、修改数据和切换图表类型。
  2. 更新 CopilotKit Runtime 测试，确认生成图表和修改样式输出不同步骤卡。

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
