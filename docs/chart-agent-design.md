# React + CopilotKit + LangGraph + ECharts 图表 Agent 实现设计

## 1. 目标概述

实现一个对话式图表生成与编辑系统：

- 用户通过自然语言表达分析意图。
- 后端 Agent 查询数据并生成结构化图表规格 `ChartSpec`。
- 前端将 `ChartSpec` 转换为 ECharts 配置并渲染。
- 后续用户可以继续通过对话修改图表，例如改颜色、换图表类型、增加指标列、调整筛选条件。
- CopilotKit 用于连接前端 UI、当前图表上下文和后端 Agent。
- LangGraph 用于后端 Agent 编排。
- ECharts 用于图表渲染。

核心原则：

> 大模型生成受控的图表规格，不直接生成 React 组件，也不直接生成任意 ECharts option。前端负责校验、转换和渲染。

## 2. 技术栈定位

采用以下技术组合：

```text
React Vite/SPA
  + CopilotKit
  + FastAPI
  + LangGraph
  + ECharts
```

职责划分：

| 模块 | 职责 |
|---|---|
| React | 页面状态、图表容器、用户交互、ECharts 渲染 |
| CopilotKit | 对话 UI、前端上下文暴露、前端 action 调用 |
| FastAPI | 后端 HTTP/流式接口 |
| LangGraph | Agent 状态机、节点编排、工具调用 |
| LLM | 意图理解、生成 ChartSpec / ChartPatch |
| Python 数据层 | 查库、权限校验、指标计算、聚合 |
| ECharts | 根据前端生成的 option 渲染图表 |

推荐数据流：

```text
用户自然语言
  -> CopilotKit 侧边栏
  -> React 发送 message + currentChart + pageContext
  -> FastAPI
  -> LangGraph ChartAgent
  -> 数据工具查询数据
  -> 生成 ChartSpec / ChartPatch
  -> 校验输出
  -> 返回 chart action
  -> React 更新 chartSpec
  -> 转换为 ECharts option
  -> 渲染图表
```

## 3. Agent 数量设计

V1 推荐只做：

```text
1 个 ChartAgent
+ 多个 LangGraph 节点
+ 多个后端工具
```

不要一开始拆成多个 Agent。

推荐原因：

- 当前任务都围绕同一个对象：当前图表 `ChartSpec`。
- 多 Agent 会增加状态同步、上下文传递、调试和成本。
- 样式修改、数据修改、换图表类型都可以由一个 LangGraph workflow 路由处理。
- 后续复杂 BI、自动 dashboard、异常归因再考虑拆 Agent。

V1 后端结构：

```text
ChartAgent
  ├─ classify_intent
  ├─ resolve_data_requirements
  ├─ query_metrics
  ├─ generate_chart_spec_or_patch
  ├─ validate_output
  └─ respond
```

未来可扩展：

```text
V1:
  ChartAgent

V2:
  ChartAgent
  + DataPlanner 节点或子模块

V3:
  Coordinator Agent
  Data Analyst Agent
  Chart Designer Agent
  Dashboard Agent
```

## 4. 后端整体架构

后端分为 5 层：

```text
FastAPI API 层
  -> LangGraph Agent 层
  -> Tool 工具层
  -> Data Service 数据层
  -> Schema / Validator 层
```

### 4.1 FastAPI API 层

负责接收前端请求。

请求结构建议：

```json
{
  "conversationId": "conv_123",
  "message": "把华东改成红色，再加一列利润率",
  "currentChart": {},
  "pageContext": {},
  "userContext": {
    "userId": "u_123",
    "tenantId": "t_456"
  }
}
```

响应方式：

- 推荐：流式文本 + 最终结构化 action。
- MVP 也可以先返回一次性 JSON。

推荐事件类型：

```text
message_delta
tool_status
chart_action
done
error
```

## 5. LangGraph Agent 设计

### 5.1 状态定义

推荐状态：

```python
class ChartAgentState(TypedDict):
    conversation_id: str
    user_message: str
    current_chart: ChartSpec | None
    page_context: dict
    user_context: UserContext

    intent: Literal[
        "create_chart",
        "update_style",
        "update_data",
        "change_chart_type",
        "explain_chart",
        "unknown"
    ]

    data_requirements: DataRequirements | None
    queried_data: QueryResult | None

    chart_action: ChartAgentAction | None
    assistant_message: str
    errors: list[str]
```

### 5.2 工作流

推荐 LangGraph 流程：

```text
start
  -> classify_intent
  -> route_by_intent

route_by_intent:
  create_chart       -> plan_data -> query_data -> generate_chart
  update_style       -> generate_style_patch
  update_data        -> plan_data -> query_data -> generate_data_patch
  change_chart_type  -> generate_type_patch
  explain_chart      -> explain_chart
  unknown            -> ask_clarification

all paths:
  -> validate_chart_action
  -> respond
```

### 5.3 意图类型

V1 支持：

```text
create_chart
update_style
update_data
change_chart_type
explain_chart
unknown
```

示例：

| 用户输入 | intent | 是否查数据 |
|---|---|---|
| 看最近 30 天各渠道销售额 | create_chart | 是 |
| 把抖音改成红色 | update_style | 否 |
| 加一列利润率 | update_data | 是 |
| 换成折线图 | change_chart_type | 视情况 |
| 解释一下这个图 | explain_chart | 否 |
| 帮我优化一下 | unknown / clarify | 否 |

## 6. ChartSpec 协议

不要让模型直接输出完整 ECharts option。定义中间协议 `ChartSpec`。

```ts
type ChartSpec = {
  id: string
  title: string
  chartType: "bar" | "line" | "pie" | "scatter" | "table"

  data: {
    columns: Array<{
      key: string
      label: string
      type: "string" | "number" | "date" | "currency" | "percent"
    }>
    rows: Record<string, unknown>[]
  }

  encoding: {
    x?: string
    y?: string
    series?: string
    category?: string
    value?: string
  }

  style: {
    visibleColumns?: string[]
    colors?: Record<string, string>
    showLegend?: boolean
    showTooltip?: boolean
    stacked?: boolean
    smooth?: boolean
    columnStyles?: Record<string, {
      color?: string
      backgroundColor?: string
      width?: number
    }>
  }
}
```

前端负责：

```text
ChartSpec
  -> validateChartSpec
  -> normalizeChartSpec
  -> toEChartsOption
  -> render
```

## 7. Chart Action 协议

后端返回的结构化 action：

```ts
type ChartAgentAction =
  | {
      type: "create_chart"
      chart: ChartSpec
      message: string
    }
  | {
      type: "update_chart"
      chartId: string
      patch: Partial<ChartSpec>
      message: string
    }
  | {
      type: "replace_chart_data"
      chartId: string
      data: ChartSpec["data"]
      message: string
    }
```

前端处理规则：

```text
create_chart:
  校验完整 ChartSpec
  通过后 setChartSpec(chart)

update_chart:
  校验 patch
  merge 到当前 ChartSpec
  再校验完整 ChartSpec

replace_chart_data:
  替换 data
  校验 encoding 字段仍然存在
  重新渲染
```

## 8. 后端工具设计

### 8.1 queryMetrics

查询聚合指标。Agent 不直接写 SQL。

```python
query_metrics(
    metrics: list[str],
    dimensions: list[str],
    filters: dict,
    time_range: TimeRange | None,
    limit: int = 500
) -> QueryResult
```

示例用途：

```text
销售额按地区
利润率按月份
订单数按渠道
用户增长趋势
```

### 8.2 getMetricCatalog

告诉 Agent 可用指标、维度、字段。

```python
get_metric_catalog(user_context) -> MetricCatalog
```

示例返回：

```json
{
  "metrics": [
    { "key": "sales", "label": "销售额", "type": "currency" },
    { "key": "profit_rate", "label": "利润率", "type": "percent" }
  ],
  "dimensions": [
    { "key": "region", "label": "地区" },
    { "key": "channel", "label": "渠道" }
  ]
}
```

这个工具很重要，用于避免模型凭空编字段。

### 8.3 validateDataAccess

权限校验。

```python
validate_data_access(
    user_context,
    metrics: list[str],
    dimensions: list[str]
) -> AccessResult
```

用于防止 Agent 查询用户无权访问的数据。

### 8.4 validateChartSpec

校验图表输出。

```python
validate_chart_spec(chart_spec: ChartSpec) -> ValidationResult
```

需要检查：

```text
chartType 是否支持
encoding.x/y/series 是否存在于 columns
visibleColumns 是否存在于 columns
颜色是否合法
rows 是否超限
表格列是否存在
饼图是否有 category/value
折线图 x 轴是否适合排序
```

## 9. 典型场景流程

### 9.1 生成新图表

用户：

```text
看一下最近 30 天各渠道销售额
```

后端流程：

```text
classify_intent -> create_chart
getMetricCatalog
plan_data -> sales by channel, last 30 days
validateDataAccess
queryMetrics
generateChartSpec
validateChartSpec
respond create_chart
```

返回：

```json
{
  "type": "create_chart",
  "chart": {},
  "message": "已生成最近 30 天各渠道销售额柱状图。"
}
```

### 9.2 修改样式

用户：

```text
把抖音这根柱子改成红色
```

后端流程：

```text
classify_intent -> update_style
read current_chart
generateStylePatch
validatePatch
respond update_chart
```

不需要查数据。

### 9.3 新增指标

用户：

```text
加一列利润率
```

后端流程：

```text
classify_intent -> update_data
getMetricCatalog
plan_data -> add profit_rate
validateDataAccess
queryMetrics
mergeData
generateDataPatch
validateChartSpec
respond update_chart / replace_chart_data
```

需要查数据。

### 9.4 换图表类型

用户：

```text
换成折线图
```

后端流程：

```text
classify_intent -> change_chart_type
check current_chart
decide encoding
validate line chart suitability
generate patch
respond update_chart
```

如果当前数据不适合折线图，返回解释：

```text
当前数据更适合柱状图。如果要看趋势，可以按日期重新聚合后生成折线图。
```

## 10. 前端设计要点

前端维护：

```ts
const [chartSpec, setChartSpec] = useState<ChartSpec | null>(null)
```

通过 CopilotKit 暴露当前图表上下文：

```tsx
useCopilotReadable({
  description: "当前图表配置 ChartSpec",
  value: chartSpec,
})
```

注册前端 actions：

```ts
createChart(chart)
updateChart(chartId, patch)
replaceChartData(chartId, data)
setChartType(chartId, chartType)
applyChartStyle(chartId, style)
```

MVP 可以只暴露两个：

```ts
createChart(chart)
updateChart(chartId, patch)
```

前端必须做校验：

```text
收到 action
  -> validate payload
  -> update chartSpec
  -> validate full chartSpec
  -> convert to ECharts option
  -> render
```

## 11. 状态和记忆设计

V1 不做复杂长期记忆。

保留三类状态：

```text
前端状态:
  当前 chartSpec

请求上下文:
  每轮请求把 currentChart 发给后端

LangGraph state:
  当前轮推理状态
```

可选 Redis：

```text
conversationId -> 最近几轮消息 + chartSpec
```

MVP 可以不加 Redis，前端每次传当前 `chartSpec` 即可。

## 12. 校验与安全

模型输出不能直接渲染。

必须校验：

```text
字段是否存在
指标是否存在
用户是否有权限
图表类型是否合法
encoding 是否匹配图表类型
rows 数量是否超限
颜色是否合法
patch 是否破坏原 ChartSpec
```

数据访问原则：

```text
Agent 不直接写 SQL
Agent 只能调用 queryMetrics
queryMetrics 内部做权限、指标白名单、维度白名单、过滤条件校验
```

## 13. 测试计划

### 13.1 单元测试

```text
ChartSpec 校验
ChartSpec -> EChartsOption 转换
ChartPatch 合并
无效颜色拒绝
不存在字段拒绝
非法 chartType 拒绝
```

### 13.2 后端测试

```text
生成销售额柱状图时调用 queryMetrics 并返回 create_chart
修改颜色时不调用 queryMetrics
新增利润率时调用 queryMetrics 并返回数据更新
无权限指标返回错误
空数据返回可解释提示
```

### 13.3 集成测试

```text
用户输入自然语言后生成图表
后续对话可修改颜色
后续对话可增加指标列
后续对话可切换图表类型
流式文本正常展示
最终 chart_action 正确更新前端状态
```

## 14. V1 范围

V1 包含：

```text
单图表生成
单图表编辑
常规图表类型
会话内状态
后端统一查数据
ChartSpec 协议
CopilotKit 侧边栏
FastAPI + LangGraph 后端
```

V1 不包含：

```text
多图 dashboard
图表持久化
图表分享
复杂下钻
多图联动
自动归因分析
Agent 直接写 SQL
LLM 直接生成 React 组件
LLM 直接生成任意 ECharts option
```

## 15. 关键实现原则

1. 一个 ChartAgent 足够，不要过早多 Agent。
2. Agent 负责理解意图、查数据、生成结构化结果。
3. 前端负责状态、校验、转换、渲染。
4. ECharts option 必须由前端从 `ChartSpec` 派生。
5. 后端数据查询必须通过受控语义指标工具。
6. 当前图表状态必须每轮传给后端，否则无法支持“把这个改成红色”这类上下文指令。
7. 样式修改优先走 patch，不重新查数据。
8. 新增指标、筛选、时间范围变化需要重新查数据。
9. 所有模型输出都要校验后再使用。
10. MVP 先把单图表对话闭环做稳，再扩展 dashboard 和多 Agent。
