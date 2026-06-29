# 前端工程规范

本文档定义 chart-agent 前端的工程边界、状态管理、CopilotKit 接入和图表渲染规则。前端当前定位是：提供 CopilotKit 对话入口，维护当前 `ChartSpec`，校验并应用后端返回的受控 `ChartAgentAction`，最终渲染 ECharts 图表。

## 分层边界

```text
frontend/src/
  components/   React 组件和 CopilotKit UI 接入
  lib/          ChartSpec runtime、配置、工具函数、ECharts option 转换
  types/        前端协议类型
  domain/       前端领域常量和受控枚举
```

要求：

- 组件只负责 UI 和用户交互，不写复杂业务决策。
- 图表业务校验放在 `lib/chartSpec.ts`。
- ECharts option 转换放在 `lib/echartsOption.ts`。
- 前端协议类型必须与后端 schema 保持一致。
- 新增常量、枚举或关键词优先收敛到 `domain/` 或专用常量文件。

## CopilotKit 使用边界

当前阶段 CopilotKit 负责：

- `CopilotKitProvider`：Runtime 接入。
- `CopilotSidebar`：自然语言对话入口。
- `useAgentContext`：当前图表上下文传递。
- `useRenderTool(chartAgentProgress)`：步骤面板渲染。
- `useRenderTool(chartAgentAction)`：接收后端图表动作。

禁止：

- 新增普通聊天框作为替代入口。
- 未经架构确认注册业务型 `useFrontendTool`。
- 在前端直接执行“创建图表、修改图表、查询数据”等 Agent 业务工具。
- 通过隐藏文本 marker 传递图表 action。

## ChartSpec 与状态同步

- `ChartSpec` 是前端图表渲染的唯一数据源。
- `ChartAgentAction` 是后端修改前端图表的唯一动作协议。
- `applyChartAction` 必须校验 action 和合并后的 chart。
- `currentChart` 必须随 CopilotKit 请求传给 Runtime/后端。
- Runtime SSE 中的 action 应通过 `actionId` 去重，避免重复应用。

## ECharts 渲染规则

- ECharts option 必须由受控 `ChartSpec` 派生。
- 不允许后端或 LLM 直接下发任意 ECharts option。
- 隐藏类目、颜色、可见列等展示状态应归属于 `ChartStyle`。
- 表格和图形图表必须共享同一份 `ChartSpec` 数据和样式语义。

## 魔法值与枚举

前端禁止新增散落的魔法字符串。以下内容必须集中维护：

- chart type
- action type
- style key
- intent 文案映射
- CopilotKit tool name
- 颜色值
- 固定代理路径和配置 key

建议后续结构：

```text
frontend/src/domain/
  chartTypes.ts
  chartActions.ts
  colors.ts
  copilotTools.ts
```

迁移规则：

- `types/` 定义 TypeScript 类型。
- `domain/` 定义运行时常量、集合和映射。
- 业务判断引用 `domain/`，避免直接写字符串。

## UI 和交互规则

- 主工作区优先展示图表、状态和必要控制，不做营销式首页。
- 执行状态展示在 CopilotKit 原生聊天消息中。
- 关键 UI 文案使用中文。
- 图表生成、修改、问答的反馈必须能从 CopilotKit 消息和主图表状态中对应起来。

## 构建和测试

前端改动至少运行：

```powershell
cd frontend
npm.cmd run build
```

涉及 CopilotKit、Runtime、上下文传递或图表交互时，必须运行：

```powershell
cd frontend
npm.cmd run test:e2e
```

新增 E2E 应优先覆盖用户真实连续流程，而不是只检查静态页面元素。
## 生成式 UI 边界

生成式 UI 采用受控 UI Blocks，而不是让 LLM 直接生成 React 代码。

要求：

- 前端只渲染白名单 `uiBlocks`。
- `uiBlocks` 必须经过运行时校验后再渲染。
- `uiBlocks` 只负责指标摘要、洞察、建议操作和辅助展示，不直接修改 `ChartSpec`。
- 图表状态变更仍然只能通过 `ChartAgentAction` 和 `applyChartAction`。
- suggested action 点击后应转成自然语言指令，继续走 CopilotKit / Runtime / Backend 链路。
- 非法 block type 或非法 payload 应降级为不渲染，不能让页面崩溃。

详细设计见 [受控生成式 UI 设计](generative-ui-design.md)。
