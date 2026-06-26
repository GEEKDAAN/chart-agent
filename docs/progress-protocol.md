# CopilotKit 工具事件协议

当前前端通过 CopilotKit `useRenderTool` 渲染和消费两个工具事件：

- `chartAgentProgress`
- `chartAgentAction`

## chartAgentProgress

职责：展示 Agent 执行步骤。

Runtime 在生成图表或修改图表时输出该工具事件。当前图表问答、闲聊、帮助和边界提示不输出步骤卡。

Payload：

```ts
type ProgressSnapshot = {
  progressId: string;
  sequence: number;
  isFinal?: boolean;
  steps: Array<{
    id: string;
    title: string;
    detail: string;
    status: "pending" | "running" | "completed" | "failed";
  }>;
};
```

维护规则：

- `progressId` 对应一次工具调用。
- `sequence` 用于前端去重和排序。
- `isFinal=true` 表示最终快照。
- 前端会按最小可见时长播放快照，避免步骤一闪而过。

## chartAgentAction

职责：传递图表创建和修改动作。

Runtime 在后端返回 `create_chart` 或 `update_chart` 时输出该工具事件。当前图表问答和闲聊类回复不输出该事件。

Payload：

```ts
type ChartAgentActionPayload = {
  actionId: string;
  action: ChartAgentAction;
};
```

维护规则：

- `actionId` 用于前端去重。
- `action` 必须符合前后端共享的 `ChartAgentAction` 协议。
- assistant 文本只保留自然语言回复，不携带隐藏 action marker。

## 职责边界

- FastAPI：生成并校验 `ChartAgentAction`。
- Node Runtime：把后端结果转换为 CopilotKit / AG-UI 工具事件。
- React：渲染步骤面板，应用图表动作。

## 当前限制

- FastAPI 业务接口仍是非流式 JSON，Runtime 根据最终结果输出多段步骤快照。
- 前端仍通过 SSE 观察器镜像工具结果，用于快速应用动作和播放进度。
- 后续如果 FastAPI 增加内部流式 endpoint，可以让 Runtime 转换真实节点级进度。
## chartAgentUiBlocks 规划

后续生成式 UI 阶段会新增 `chartAgentUiBlocks` 工具事件，用于在 CopilotKit 原生聊天消息内渲染受控 UI Blocks，例如指标摘要、洞察卡片、建议操作和轻量明细表。

该事件只负责展示增强，不修改图表状态。图表创建和修改仍然只能通过 `chartAgentAction` 传递，并由前端校验后应用到 `ChartSpec`。

Payload 方向：

```ts
type ChartAgentUiBlocksPayload = {
  uiBlockId: string;
  blocks: ChartAgentUiBlock[];
};
```

维护规则：

- `uiBlockId` 用于前端去重。
- `blocks` 必须是白名单 block type。
- 非法 block type 或非法 payload 应被忽略或降级，不能导致页面崩溃。
- suggested action 点击后应回到自然语言请求链路，不直接修改图表。

详细设计见 [受控生成式 UI 设计](generative-ui-design.md)。
