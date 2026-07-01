# 真实数据源接入设计

当前项目使用 mock 指标服务验证图表 Agent 链路。后续接入真实数据源时，目标不是让 Agent 直接查询数据库，而是通过受控指标层暴露稳定、可校验、可审计的数据能力。

## 设计目标

- Agent 只表达“需要什么指标、维度、筛选和时间范围”。
- 数据访问由指标服务或数据源适配器执行。
- 所有指标、维度、过滤条件和权限都必须可枚举、可校验。
- 不允许 LLM 直接生成 SQL。
- 不允许前端绕过后端 Agent 查询业务数据。

## 当前接口

后端当前通过 `backend/app/services/metrics.py` 暴露三个核心函数：

```text
get_metric_catalog(user_context)
validate_data_access(user_context, metrics, dimensions)
query_metrics(metrics, dimensions, filters, time_range, limit)
```

这三个函数是未来替换 mock 数据源的主要边界。Agent workflow 不应该直接感知数据库、表名或 BI 平台细节。

## 建议结构

```text
Agent
  -> DataRequirements
  -> MetricCatalog
  -> AccessPolicy
  -> MetricQueryService
  -> DataSourceAdapter
  -> Real data platform
```

### MetricCatalog

指标目录负责定义：

- 指标 key、中文名、类型和单位。
- 可用维度。
- 默认聚合方式。
- 可用筛选字段。
- 是否允许按当前租户或用户访问。

示例：

```json
{
  "metric": "sales",
  "label": "销售额",
  "type": "currency",
  "dimensions": ["date", "region", "channel"],
  "defaultAggregation": "sum"
}
```

### AccessPolicy

权限层负责校验：

- 用户是否属于当前租户。
- 用户是否可访问某个指标。
- 用户是否可访问某些维度或筛选值。
- 查询时间范围是否超过限制。
- 查询结果行数是否超过限制。

### MetricQueryService

查询服务负责把受控数据需求转换为真实查询请求。它可以调用：

- 内部指标平台 API。
- BI 平台 API。
- 只读查询服务。
- 数据仓库中经过白名单模板管理的查询。

### DataSourceAdapter

适配器负责对接具体数据源。建议每类数据源一个实现：

- `MockMetricDataSource`
- `HttpMetricDataSource`
- `SqlTemplateMetricDataSource`
- `BiApiMetricDataSource`

Agent 只依赖统一接口，不依赖具体实现。

## 请求结构

真实数据源阶段建议继续使用当前语义结构：

```json
{
  "metrics": ["sales"],
  "dimensions": ["channel"],
  "filters": {
    "region": ["华东"]
  },
  "timeRange": {
    "type": "relative",
    "value": "30d"
  },
  "limit": 500
}
```

所有字段都应先经过目录和权限校验，再进入真实查询层。

## 错误处理

需要区分以下错误：

- 指标不存在。
- 维度不支持。
- 筛选值不允许。
- 权限不足。
- 查询超时。
- 数据源不可用。
- 返回数据不符合 `ChartData` schema。

错误应转换为可读的 `ChartAgentAction(type="error")`，不要把底层 SQL、堆栈或内部 API 地址暴露给前端。

## 迁移步骤

1. 保持 mock 数据源不变，先抽象 `MetricDataSource` 协议。
2. 增加真实数据源适配器，但默认不开启。
3. 增加 `.env.example` 配置项，例如数据源 URL、超时、模式开关。
4. 为真实数据源适配器补契约测试。
5. 在开发环境以只读方式验证真实数据。
6. 再接入 Agent 默认链路。

## 风险

- 指标目录不清晰会导致 LLM 和 fallback 都难以稳定解析需求。
- 真实数据延迟会影响 CopilotKit 聊天体验。
- 权限模型不完整会带来数据泄露风险。
- 如果直接把 SQL 能力暴露给 Agent，会破坏当前受控架构边界。
