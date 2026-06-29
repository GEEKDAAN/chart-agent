# 公开展示检查清单

本文档用于在项目公开前做最终确认，目标是让外部读者能够快速理解项目、启动项目，并确认仓库中没有不适合公开的内容。

## 必须确认

- README 能说明项目是什么、解决什么问题、如何启动和如何验证。
- `backend/.env.example`、`frontend/.env.example` 不包含真实密钥。
- 根目录不存在被跟踪的 `.env`、日志、截图、测试报告、构建产物或临时目录。
- `CHANGELOG.md` 已记录当前版本改动。
- `docs/` 中公开文档和内部过程文档已分层。
- 默认启动模式使用 `CHART_AGENT_LLM_MODE=off`，避免外部读者必须准备大模型 key 才能体验基础链路。

## 建议补充

- 持续更新项目截图或 GIF，展示图表生成、连续编辑和受控生成式 UI。
- 明确许可证，例如 MIT、Apache-2.0 或保留全部权利。
- 增加部署说明，说明三服务在生产环境中的部署方式。
- 增加 Roadmap，区分已实现、计划实现和暂不计划实现的能力。
- 增加真实数据源接入设计，说明指标目录、权限和查询服务如何替换 mock。

## 公开前命令

```powershell
git status --short
git ls-files .env* outputs tmp work frontend/test-results frontend/playwright-report
cd runtime
npm.cmd run check:text
```

如涉及代码或协议调整，还需要按 [测试规范](testing-guidelines.md) 执行后端、Runtime、前端和 E2E 测试。

## 当前限制说明

公开展示时需要明确当前项目仍是原型到可展示阶段：

- 当前数据源是 mock 指标服务。
- 暂无用户体系、权限体系和持久化。
- 暂无生产级部署脚本和 CI/CD。
- 生成式 UI 采用白名单 `uiBlocks`，不是任意 React 代码生成。
