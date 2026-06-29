# 后端工程规范

本文档定义 chart-agent 后端的代码结构、协议边界和可维护性规则。后端当前定位是：FastAPI 提供业务接口，LangGraph 编排 Agent workflow，服务层实现确定性逻辑和 LLM 兜底能力。

## 分层边界

```text
backend/app/
  routers/      HTTP 路由，只负责请求模型、响应模型和入口调用
  agents/       LangGraph workflow 编排和节点连接
  services/     业务服务、意图决策、数据需求解析、指标查询、样式修改
  schemas/      外部协议和内部结构化模型
  core/         配置、环境变量和基础设施
  domain/       领域常量、枚举、关键词和受控集合
```

要求：

- `routers/` 不写业务规则。
- `agents/` 不写大段领域判断，只编排节点和调用 service。
- `services/` 可以实现业务逻辑，但应按领域拆分，不把 LLM 调用、fallback 规则、问答逻辑和 guardrail 长期塞在一个文件。
- `schemas/` 是协议结构来源；schema 变更必须同步测试和更新日志。
- `domain/` 是领域常量入口，新增枚举或关键词优先放这里。

## Agent 决策规则

后端采用“LLM-first + backend guardrails”的决策模型：

1. 先生成确定性 fallback 决策，保证 LLM 不可用时系统基础可用。
2. 再尝试 LLM 结构化决策。
3. LLM 决策必须满足 schema、置信度、工具/意图匹配和冲突校验。
4. 低置信度、非法工具、非法参数、与确定性强信号冲突时，必须回退 fallback。

推荐意图优先级：

```text
闲聊 / 帮助 / 越界
样式修改 / 隐藏 / 恢复显示
结构修改 / 新增指标 / 切换图表类型
新图表请求 / 新维度 / 新指标 / 新时间范围组合
当前图表问答
澄清
```

新增意图时必须先写入决策矩阵测试，再实现规则或 LLM guardrail。

## 受控 Action 规则

外部动作只允许：

- `create_chart`
- `update_chart`
- `error`

禁止：

- 让 LLM 返回任意 ECharts option。
- 让 LLM 返回任意 React 组件。
- 在前端绕过 `ChartAgentAction` 直接执行业务修改。
- 在 action patch 中携带 schema 未定义字段。

要求：

- 创建图表返回完整 `ChartSpec`。
- 修改图表返回受控 `ChartPatch`。
- 样式修改、隐藏类目、恢复显示、切换类型、数据更新都必须走后端受控工具。
- action 生成后必须经过 `ChartAgentAction` 校验。

## 魔法值与枚举

禁止新增散落的魔法字符串。以下内容必须集中定义：

- intent：如 `create_chart`、`update_style`。
- tool name：如 `answer_current_chart_question`。
- chart type：如 `bar`、`line`。
- action type：如 `create_chart`、`update_chart`。
- metric key：如 `sales`、`orders`。
- dimension key：如 `channel`、`date`。
- 颜色名称、颜色 hex、颜色中文 label。
- progress step id 和 intent 对应模板。

建议后续结构：

```text
backend/app/domain/
  intents.py
  chart_types.py
  metrics.py
  dimensions.py
  colors.py
  progress.py
```

迁移规则：

- schema 中的 `Literal` 可以保留。
- 业务判断应引用 `domain/` 常量或集合。
- 新增枚举值必须同步 schema、domain、测试和更新日志。

## 数据需求解析

数据需求解析负责把自然语言转换为受控查询需求：

- metrics
- dimensions
- filters
- time_range
- limit

规则：

- Agent 不直接写 SQL。
- 数据查询只能走受控指标服务。
- 新增指标或维度必须更新关键词、mock 数据、权限校验和测试。
- 时间范围解析必须保持确定性，避免依赖当前自然语言模型输出。

## LLM 调用规范

- LLM 输出必须是结构化 JSON。
- LLM 输出必须经过 Pydantic/schema 校验。
- LLM 不可用时不能导致核心路径不可用。
- 不在日志、测试快照或文档中泄露真实 API key。
- prompt 更新必须补充或调整对应测试。

## 测试分层

后端测试应分层维护：

```text
backend/tests/
  test_chart_agent_api.py          HTTP API 契约
  test_chart_agent_graph.py        LangGraph workflow 行为
  test_intent_decision_matrix.py   意图决策矩阵
  test_llm_decisions.py            LLM 决策和 guardrail
  test_data_requirements.py        数据需求解析
  test_metrics.py                  指标服务
```

新增后端能力至少补一个测试层；涉及意图判断时必须补 `test_intent_decision_matrix.py`。

## 版本和更新日志

- 后端版本号在 `backend/app/main.py`。
- 每个已验收版本必须更新 `CHANGELOG.md`。
- 修改后端协议、意图、工具或 action 时，更新日志必须说明用户可感知影响和测试覆盖。
## 生成式 UI 边界

后端可以在后续版本返回受控 `uiBlocks`，用于指标摘要、洞察卡片、建议操作和辅助明细展示。

要求：

- `uiBlocks` 必须是结构化 JSON。
- `uiBlocks` 必须经过 Pydantic/schema 校验。
- block type 必须集中定义在 `domain/`。
- LLM 不可用时应使用 deterministic fallback 生成基础摘要，或不返回 `uiBlocks`。
- `uiBlocks` 不能绕过 `ChartAgentAction` 修改图表状态。

禁止：

- 返回 React 代码。
- 返回任意 HTML。
- 返回任意 ECharts option。
- 在 `uiBlocks` 中携带未经校验的业务执行指令。

详细设计见 [受控生成式 UI 设计](generative-ui-design.md)。
