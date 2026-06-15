# CopilotKit 执行进度协议

本文档记录 `chartAgentProgress` 的当前维护边界，避免后续把状态展示、业务执行和上下文注入混在同一层。

## 职责边界

- FastAPI LangGraph Agent 负责真实业务执行和图表 action 生成。
- Node CopilotKit Runtime 负责把步骤状态转换为 AG-UI tool call SSE 事件。
- 前端 CopilotKit `useRenderTool(chartAgentProgress)` 负责把工具调用渲染在原生聊天消息内。
- 前端 `chartAgentProgressStore` 只负责按 `progressId + sequence` 播放快照，不参与业务判断。
- 当前阶段不注册业务型 `useFrontendTool`，避免前后端形成两套执行通道。

## 后端输出

后端只在会改变图表的工具上输出进度卡：

- `create_chart`
- `update_style`
- `update_data`
- `change_chart_type`

当前图表问答、闲聊、帮助和边界提示不输出 `chartAgentProgress`，也不返回 `chart-agent-action` marker。

## Payload

`chartAgentProgress` 参数和结果使用同一结构：

```json
{
  "progressId": "tool-xxx",
  "sequence": 2,
  "isFinal": false,
  "steps": [
    {
      "id": "query_data",
      "title": "查询业务数据",
      "detail": "已获得图表所需数据",
      "status": "completed"
    }
  ]
}
```

字段说明：

- `progressId`：一次 CopilotKit 工具调用的稳定 ID，前端用它订阅同一张步骤卡。
- `sequence`：递增序号，前端用于去重和按顺序播放快照。
- `isFinal`：最终快照标记，当前用于调试和后续清理策略。
- `steps[].status`：仅允许 `pending`、`running`、`completed`、`failed`。

## 维护规则

新增或修改步骤时优先调整：

- Runtime：`runtime/src/progress.ts`
- 前端类型：`frontend/src/types/progress.ts`
- 前端渲染：`frontend/src/components/CopilotKitPanel.tsx`
- E2E 测试：`frontend/e2e/copilotkit-chart-agent.spec.ts`

不要在 FastAPI 业务后端中新增 CopilotKit Runtime 协议逻辑。当前 PoC 中 `/copilotkit` 入口由 `runtime/` 负责。

## 当前限制

- `0.11.0` PoC 暂时只恢复开始/完成快照，尚未恢复 `0.10.3` 的 LangGraph 节点级连续流转。
- 前端通过 `fetch` patch 镜像 CopilotKit SSE，属于过渡实现；切换官方完整 Runtime SDK 时应优先评估是否能移除这层 patch。
- 最小展示时长由前端控制，因此视觉进度可能略晚于后端真实完成时间。
