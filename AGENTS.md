# BeerAgentCodeCore

BeerCode：用 Python 从零构建的 Claude Code 风格终端 AI 编程助手，教学实践项目。

## 开发约定

- 始终用中文回复用户。
- 项目代码中不写注释。
- 逐个功能推进：一个功能对应一个 GitHub Issue，完成后打 tag（如 `step-01-chat`），不提前实现后续功能。
- 功能开发完成后，必须用 tmux 做端到端测试（pytest 驱动 `tmux send-keys` / `capture-pane`，后端使用本地模拟服务器）。
- 不提交 `beercode.yaml` 等含密钥的文件，示例配置放在 `beercode.example.yaml`。

## Agent skills

### Issue tracker

Issues live in GitHub Issues for `HUA1255/BeerAgentCodeCore` (via the `gh` CLI). See `docs/agents/issue-tracker.md`.

### Triage labels

Default vocabulary: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: one `GLOSSARY.md` plus `docs/adr/` at the repo root. See `docs/agents/domain.md`.
