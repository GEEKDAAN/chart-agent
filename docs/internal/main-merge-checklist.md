# Runtime PoC 合并主线清单

## 当前状态

- 当前候选分支：`codex/copilotkit-runtime-poc`
- 合并目标分支：`main`
- 当前候选版本：`0.11.6`
- 合并基础提交：`9e6a91e`
- 候选分支新增提交数：7
- Git 合并树检查：通过，无文件级冲突

注意：本地 `main` 当前比 `origin/main` 超前 4 个提交。合并前需要先确认本地 `main` 是否就是准备推送到远端的主线状态。

## 合并会引入的核心变化

### 架构变化

合并后项目从两服务开发形态变为三服务开发形态：

```text
Vite frontend
  -> Node CopilotKit Runtime
  -> FastAPI chart-agent backend
```

FastAPI 只保留图表业务接口，不再承载 CopilotKit Runtime。

### 删除内容

合并会删除 FastAPI 自研 CopilotKit Runtime 相关代码：

- `backend/app/routers/copilotkit.py`
- `backend/app/services/progress.py`
- `backend/tests/test_copilotkit_runtime.py`

删除原因：

- Runtime 入口迁移到官方 `@copilotkit/runtime/v2` Node 服务。
- 进度事件生成迁移到 `runtime/src/progress.ts`。
- Runtime 协议测试迁移到 `runtime/tests/chart-agent.test.ts`。

### 新增内容

合并会新增：

- `runtime/`：官方 CopilotKit Runtime SDK PoC 服务。
- `scripts/dev.ps1`：三服务统一启动脚本。
- `scripts/stop-dev.ps1`：三服务停止脚本。
- `scripts/check-text-encoding.ps1`：中文编码检查脚本。
- `docs/local-development.md`：三服务本地开发说明。
- `docs/internal/copilotkit-runtime-poc.md`：Runtime PoC 评估说明。
- `docs/internal/runtime-poc-merge-review.md`：合并前技术审查。

## 合并前必须确认

1. 接受新增 Node Runtime 服务。
2. 接受 `/copilotkit` 不再由 FastAPI 提供。
3. 接受本地开发默认需要同时运行 FastAPI、Node Runtime、Vite。
4. 接受当前仍保留前端 `fetch` patch 作为 CopilotKit 上下文传递兜底。
5. 接受当前步骤面板是 Runtime 根据后端最终 intent 合成的进度，不是 LangGraph 节点真实流式进度。
6. 接受真实 LLM 模式仍需要人工验收，不作为自动化测试的稳定前提。

## 合并前验证命令

建议按以下顺序执行：

```powershell
cd runtime
D:\nodejs\npm.cmd run check:text
D:\nodejs\npm.cmd run test
D:\nodejs\npm.cmd run build
```

```powershell
cd backend
$env:CHART_AGENT_LLM_MODE='off'
D:\python\python3.11.2\python.exe -m pytest -q
```

```powershell
cd frontend
D:\nodejs\npm.cmd run build
```

```powershell
powershell -ExecutionPolicy Bypass -File scripts/dev.ps1 -LlmMode off -BackendPort 8012 -RuntimePort 8022 -FrontendPort 5187
```

```powershell
cd frontend
$env:E2E_FRONTEND_PORT='5187'
$env:E2E_BACKEND_PORT='8012'
$env:E2E_RUNTIME_PORT='8022'
D:\nodejs\npm.cmd run test:e2e
```

## 合并后验收路径

页面验收建议使用以下连续对话：

```text
近30天各销售渠道的销售额
有哪些渠道？
抖音的销售额有多少？
把抖音改成红色
换成折线图
```

预期：

- 第一次生成图表后，页面出现柱状图。
- “有哪些渠道？”直接回答当前图表渠道，不新增步骤面板。
- “抖音的销售额有多少？”直接回答当前图表数据，不新增步骤面板。
- “把抖音改成红色”触发步骤面板，并更新当前图表样式。
- “换成折线图”触发步骤面板，并更新图表类型。
- 聊天文本中不出现 `chart-agent-action` 或 `chart-agent-step` 隐藏 marker。

## 已知非阻断问题

- 前端构建存在 Vite 包体警告，主要来自 CopilotKit 相关依赖和大 chunk。
- 前端构建存在 `node-fetch` 浏览器 externalized 警告，目前不影响 E2E。
- 后端测试存在 Starlette/TestClient 废弃警告，目前不影响功能。
- 在当前 Codex 沙箱内，前端 Vite 构建可能因 esbuild 读取上级目录权限失败；非沙箱真实构建已验证通过。

## 合并后优先处理

1. 评估移除前端 `fetch` patch，收敛到官方 CopilotKit 上下文传递能力。
2. 设计 FastAPI 到 Node Runtime 的真实流式进度协议。
3. 增强 Node Runtime `/health`，检查 FastAPI 后端可达性。
4. 优化前端包体和 CopilotKit 相关依赖的浏览器构建警告。
5. 为真实 LLM 模式补充人工 smoke test 清单。
