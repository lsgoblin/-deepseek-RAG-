# Skills 展厅本地采集区

本目录用于保存首批图片 Skills 的本地正文快照。

- `manifest.json` 是来源、提交版本、正文哈希和发布状态的清单，可纳入版本控制。
- `<slug>/SKILL.md` 是从清单所列 GitHub 提交取得的核心正文。
- `<slug>/LICENSE.upstream` 在上游提供许可证文件时保存其原文。
- 第三方正文和许可证副本默认被 `.gitignore` 排除，避免把“已下载供本机评估”误当成“已获权可随产品分发”。

这些快照是 `content_only` 采集物，不是可执行的完整 Skill 包。正文引用的 `references/`、`scripts/`、`assets/` 等文件未在本轮下载；只有在取得相应授权并补齐依赖后，才能将条目标记为可发布包。

公开展示、商业使用或把 Skill 作为应用内置功能前，必须按 `manifest.json` 的 `publication_status` 复核许可证。`blocked_*` 条目不得发布；`restricted_review` 条目需取得与实际用途匹配的书面授权。
