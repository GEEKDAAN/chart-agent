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
